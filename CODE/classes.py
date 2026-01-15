"""Core narrative generation system with error learning.

Contains:
- Story state management (facts, objects, inconsistencies)
- Method A: generation with feedback learning
- Method B: baseline without feedback
- Historical anachronism detection
"""

import json
import os
import time

from google import genai
from google.genai import types

# API key from environment variable (more secure) or fallback for development
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyATRw_AHS34fCmObEIQvQRyUJNZOwj1JKk")

client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(api_version='v1beta')
)

# Gemini 1.5 Flash Lite model - good cost/quality tradeoff
GEMINI_MODEL = "models/gemini-flash-lite-latest"


def build_characters_from_config(config_characters):
    """Prepare characters from JSON configuration for story_state.
    
    Adds:
    - 'status' = 'alive' to each character if not present
    
    Args:
        config_characters: list of dicts with all character details
        
    Returns:
        list of dicts with characters ready for story_state
    """
    characters = []
    for char_config in config_characters:
        # Copy character as-is
        character = dict(char_config)
        # Add initial status if not present
        if "status" not in character:
            character["status"] = "alive"
        
        characters.append(character)
    
    return characters


def init_story_state(characters=None, world_config=None, initial_facts=None):
    """Initialize story state with custom configuration.
    
    Args:
        characters: list of dicts with characters
        world_config: dict with world info (setting, rules) from configuration
        initial_facts: list of initial facts
    """
    if characters is None:
        raise FileNotFoundError(
            f"Configuration file not found.\n"
            "Make sure story_config.json exists in the CODE directory."
        )
    
    if world_config is None:
        raise FileNotFoundError(
            f"Configuration file not found.\n"
            "Make sure story_config.json exists in the CODE directory."
        )
    
    if initial_facts is None:
        raise FileNotFoundError(
            f"Configuration file not found.\n"
            "Make sure story_config.json exists in the CODE directory."
        )

    return {
        "world": {
            "name": world_config.get("name", "Il Mondo"),
            "setting": world_config.get("setting", "Unknown"),
            "description": world_config.get("description", ""),
            "rules_explicit": world_config.get("rules", []),
        },
        "characters": characters,
        "items": [],  # Items dynamically created from the story
        "facts": initial_facts,
        "history": [],
        "inconsistencies": [],
    }




# Direct prompt for Gemini: narrative text only, no JSON, no header
def call_gemini(prompt, model=GEMINI_MODEL, temperature=0.7, cached_context=None):
    """Call Gemini with prompt caching support.
    
    Args:
        prompt: The main prompt
        model: Model name
        temperature: Generation temperature
        cached_context: (not used for now - free API doesn't support caching well)
    """
    # Add delay to respect rate limits
    time.sleep(12)
    
    # If there's cacheable context, prepend to prompt (simple concatenation)
    if cached_context:
        full_prompt = cached_context + "\n\n" + prompt
    else:
        full_prompt = prompt
    
    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=2048,
        )
    )
    
    # Handle empty or blocked response
    if response.text is None or not response.text:
        # Try to access candidates directly
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts and len(candidate.content.parts) > 0:
                return candidate.content.parts[0].text.strip()
            # If blocked by safety filters
            if hasattr(candidate, 'finish_reason'):
                raise ValueError(f"Response blocked or empty. Reason: {candidate.finish_reason}")
        raise ValueError("Empty response from model")
    
    return response.text.strip()


def _format_world(world):
    """Helper: format world info."""
    rules = world.get("rules_explicit", [])
    if not isinstance(rules, list):
        rules = [str(rules)]
    
    text = f"# {world.get('name', 'Il Mondo')}\n"
    text += f"Ambientazione: {world.get('setting', 'Sconosciuta')}\n"
    if world.get('description'):
        text += f"{world['description']}\n"
    if rules:
        text += "Regole: " + " | ".join(rules[:5])  # Max 5 rules, compact
    return text


def _format_characters(characters, full_details=False):
    """Helper: format characters."""
    lines = []
    for c in characters:
        name = c.get('name', '?')
        role = c.get('role', '?')
        element = c.get('element', '')
        status = c.get('status', 'alive')
        
        if full_details:
            # Full version
            traits = c.get('traits', [])  # Max 2 traits
            goals = c.get('goals', [])[:1]  # Max 1 goal
            lines.append(f"- {name} ({role}, {element}): {', '.join(traits)} | Goal: {goals[0] if goals else '?'} [{status}]")
        else:
            # Compact version
            lines.append(f"- {name} ({role}): {element} [{status}]")
    return "\n".join(lines)


def _format_facts(facts):
    """Helper: format facts."""
    if not facts:
        return "Nessun fatto."
    lines = []
    for f in facts[-10:]:  # Max last 10 facts
        if isinstance(f, dict):
            lines.append(f"- T{f.get('turn_created', '?')}: {f.get('description', '')}")
        else:
            lines.append(f"- {f}")
    return "\n".join(lines)


def format_state_for_prompt(story_state, include_full_character_details=False):
    """Format story state for prompt in compact way."""
    world_text = _format_world(story_state["world"])
    chars_text = _format_characters(story_state["characters"], include_full_character_details)
    facts_text = _format_facts(story_state["facts"])
    
    # Items only if present
    items = story_state.get("items", [])
    items_text = ""
    if items:
        items_text = "\nOggetti: " + ", ".join(f"{it.get('name', '?')}" for it in items)
    
    return f"{world_text}\n\nPersonaggi:\n{chars_text}\n\nFatti:\n{facts_text}{items_text}"

def create_cacheable_context(story_state, plot_config=None):
    """Create the FIXED part of the prompt to cache (world, rules, characters, plot).
    This part doesn't change between turns, so it can be cached to save costs."""
    world = story_state["world"]
    rules = world.get("rules_explicit", [])
    
    context = f"""# CONTESTO DELLA STORIA (FISSO)

MONDO: {world.get('name', 'Il Mondo')}
AMBIENTAZIONE: {world.get('setting', 'Sconosciuta')}
DESCRIZIONE: {world.get('description', '')}

REGOLE DEL MONDO:
{chr(10).join(f"- {r}" for r in rules) if rules else "Nessuna regola esplicita."}

PERSONAGGI:
{_format_characters(story_state['characters'], full_details=True)}
"""
    
    # Add plot structure if present
    if plot_config:
        context += f"""\nSTRUTTURA NARRATIVA:
- Evento scatenante: {plot_config.get('inciting_incident', 'N/A')}
- Complicazioni: {plot_config.get('complications', 'N/A')}
- Climax: {plot_config.get('climax', 'N/A')}
- Risoluzione: {plot_config.get('resolution', 'N/A')}
- Tema: {plot_config.get('theme', 'N/A')}
"""
    
    return context

def generate_story_step_method_B(story_state, user_input):
    """Generate story WITHOUT feedback on inconsistencies (baseline for comparison).
    
    Inconsistencies are still RECORDED in update_state_from_output,
    but they are NOT passed to the model as input.
    This allows comparing method_A (which learns) vs method_B (which doesn't learn).
    """
    state_text = format_state_for_prompt(story_state)

    # Simple prompt, WITHOUT feedback on inconsistencies (this is method_B)
    prompt = (
        "Continua la storia in italiano, 1-2 paragrafi. "
        "Stato attuale:\n" + state_text + "\n\n" +
        "Input dell'utente:\n" + user_input + "\n"
    )
    output = call_gemini(prompt)
    return output

def append_to_history(story_state, user_input, model_output):
    story_state["history"].append({
        "user": user_input,
        "assistant": model_output
    })

def update_state_from_output(story_state, new_story_chunk, turn_id):
    """Extract new facts from story and verify TRUE historical/logical inconsistencies.
    
    IMPORTANT: Reports ONLY anachronisms and physical impossibilities, NOT character behaviors."""
    
    # Prepare info for unified prompt
    explicit_rules = story_state["world"].get("rules_explicit", [])
    setting = story_state["world"].get("setting", "")
    
    # Simplified prompt: only facts, objects, and VIOLATIONS
    unified_prompt = f"""Analizza questo frammento di storia ambientato in: {setting}

REGOLE ESPLICITE DEL MONDO:
{chr(10).join(f"- {r}" for r in explicit_rules) if explicit_rules else "Nessuna regola esplicita."}

Storia da analizzare:
{new_story_chunk}

COMPITI:

1. FATTI: Eventi importanti per la trama (scoperte, scontri, rivelazioni, decisioni)

2. OGGETTI: Oggetti significativi menzionati (armi, artefatti, documenti)

3. VIOLAZIONI: Segnala SOLO questi errori:
   - ANACRONISMI: oggetti/tecnologie che non esistevano nell'epoca (es. cannocchiale nel 1380, pistole, orologi da polso, stampa in Cina prima del XV secolo)
   - IMPOSSIBILITÀ STORICHE: eventi impossibili per l'epoca (es. America prima del 1492, mongolfiere prima dei fratelli Montgolfier)
   - CONTRADDIZIONI: fatti che contraddicono quanto stabilito nella storia precedente
   
   NON segnalare:
   - Comportamenti dei personaggi
   - Decisioni tattiche
   - Violazioni di protocolli/regole interne
   - Oggetti plausibili per l'epoca (es. cristalli levigati, strumenti rudimentali in Cina 1380)

Rispondi in questo formato:

FATTI:
- [fatto 1]

OGGETTI:
- [nome] | [chi lo ha] | [stato]

VIOLAZIONI:
- [ANACRONISMO/IMPOSSIBILITÀ/CONTRADDIZIONE]: [descrizione] oppure NESSUNA

Risposta:"""
    
    try:
        unified_result = call_gemini(unified_prompt, temperature=0.2)
        
        # Initialize structures
        if "inconsistencies" not in story_state:
            story_state["inconsistencies"] = []
        
        # Parsing
        lines = unified_result.strip().split('\n')
        in_facts = False
        in_objects = False
        in_violations = False
        new_facts = []
        new_items = []
        
        for line in lines:
            line = line.strip()
            
            if "FATTI:" in line.upper():
                in_facts = True
                in_objects = False
                in_violations = False
                continue
            elif "OGGETTI:" in line.upper():
                in_facts = False
                in_objects = True
                in_violations = False
                continue
            elif "VIOLAZIONI" in line.upper():
                in_facts = False
                in_objects = False
                in_violations = True
                continue
            
            if line.startswith('-') or line.startswith('•'):
                content = line[1:].strip()
                if not content:
                    continue
                
                if in_facts:
                    new_facts.append({
                        "id": len(story_state["facts"]) + len(new_facts) + 1,
                        "description": content,
                        "turn_created": turn_id
                    })
                
                elif in_objects:
                    parts = [p.strip() for p in content.split('|')]
                    if len(parts) >= 3:
                        item_name, location, status = parts[0], parts[1], parts[2]
                    elif len(parts) == 2:
                        item_name, location, status = parts[0], parts[1], "menzionato"
                    else:
                        item_name, location, status = content, "sconosciuta", "menzionato"
                    
                    if not any(it.get("name") == item_name for it in story_state["items"]):
                        new_items.append({
                            "name": item_name,
                            "location": location,
                            "status": status,
                            "discovered_turn": turn_id
                        })
                
                elif in_violations:
                    if "NESSUNA" not in content.upper():
                        # Determine type
                        if "ANACRONISMO" in content.upper():
                            viol_type = "anacronismo"
                        elif "IMPOSSIBILITÀ" in content.upper() or "IMPOSSIBILITA" in content.upper():
                            viol_type = "impossibilità_storica"
                        elif "CONTRADDIZIONE" in content.upper():
                            viol_type = "contraddizione"
                        else:
                            viol_type = "altro"
                        
                        story_state["inconsistencies"].append({
                            "turn": turn_id,
                            "type": viol_type,
                            "description": content,
                            "story_chunk": new_story_chunk[:150] + "..."
                        })
        
        # Add facts and objects
        story_state["facts"].extend(new_facts)
        story_state["items"].extend(new_items)
        
    except Exception as e:
        print(f"[WARNING] Unable to analyze story: {e}")
    
    return story_state, new_story_chunk

def generate_story_step_method_A(story_state, user_input, plot_config=None, current_turn=0, max_turns=10, use_caching=True):
    """Complete pipeline with ERROR LEARNING and PLOT STRUCTURE.
    
    Unlike method_B:
    - Includes past inconsistencies to AVOID in the prompt
    - Includes already deduced implicit rules
    - Allows the model to learn from its own errors
    - Guides narrative pacing based on plot phase
    - USES CACHING to save costs (70% discount on fixed part)
    """
    # Create cacheable context (world, characters, plot) - FIXED for all turns
    cached_context = create_cacheable_context(story_state, plot_config) if use_caching else None
    
    # VARIABLE part: only recent facts and items
    facts_text = _format_facts(story_state["facts"])
    items = story_state.get("items", [])
    items_text = "\nOggetti: " + ", ".join(f"{it.get('name', '?')}" for it in items) if items else ""
    
    state_text = f"Fatti:\n{facts_text}{items_text}"
    
    # PLOT STRUCTURE GUIDANCE
    plot_text = ""
    if plot_config:
        # Calculate completion percentage
        progress = current_turn / max_turns if max_turns > 0 else 0
        
        if progress < 0.3:
            # Initial phase: setup and inciting incident
            phase = "FASE INIZIALE"
            plot_text = f"\n\n{phase}: Introduci conflitti e sviluppa la situazione. "
            if plot_config.get("inciting_incident"):
                plot_text += f"Evento scatenante: {plot_config['inciting_incident']}\n"
        elif progress < 0.6:
            # Central phase: complications
            phase = "FASE CENTRALE"
            plot_text = f"\n\n{phase}: Aumenta la tensione, introduci ostacoli e complicazioni. "
            if plot_config.get("complications"):
                plot_text += f"Complicazioni: {plot_config['complications']}\n"
        elif progress < 0.85:
            # Climax phase
            phase = "FASE CLIMAX"
            plot_text = f"\n\n{phase}: Stiamo avvicinandoci al climax. Prepara lo scontro decisivo. "
            if plot_config.get("climax"):
                plot_text += f"Climax previsto: {plot_config['climax']}\n"
        else:
            # Final phase: resolution - MUST conclude
            phase = "FASE FINALE"
            plot_text = f"\n\n{phase}: TURNO FINALE - CONCLUDI LA STORIA ORA!\n"
            plot_text += "OBBLIGATORIO: Questo è l'ultimo turno disponibile. Devi:\n"
            plot_text += "1. Risolvere il conflitto principale (recupero artefatto)\n"
            plot_text += "2. Concludere l'arco di Zhang Hao (scelta finale)\n"
            plot_text += "3. Chiudere con un epilogo definitivo (pace ristabilita o conseguenze)\n"
            plot_text += "NON lasciare la storia aperta o incompleta. Scrivi una CONCLUSIONE.\n"
            if plot_config.get("resolution"):
                plot_text += f"Direzione finale: {plot_config['resolution']}\n"
    
    # FEEDBACK ON PAST ERRORS (key difference vs method_B)
    learning_text = ""
    
    # Implicit rules already deduced
    implicit_rules = story_state["world"].get("implicit_rules", [])
    if implicit_rules:
        learning_text += "\n\nREGOLE IMPLICITE (dedotte dal contesto, da rispettare):\n"
        learning_text += "\n".join(f"- {r}" for r in implicit_rules[-5:])  # Max 5
    
    # Past inconsistencies to avoid - EXPLICIT AND STRONG FEEDBACK
    inconsistencies = story_state.get("inconsistencies", [])
    if inconsistencies:
        learning_text += "\n\nERRORI CRITICI DA NON RIPETERE MAI:\n"
        for inc in inconsistencies[-3:]:  # Max 3 most recent
            inc_type = inc.get('type', 'unknown')
            desc = inc['description']
            learning_text += f"- Turn {inc['turn']} ({inc_type}): {desc}\n"
        
        # Extract specific anachronistic objects to explicitly block them
        banned_objects = []
        for inc in inconsistencies:
            if inc.get('type') == 'anacronismo':
                # Extract keywords to ban
                desc_lower = inc['description'].lower()
                if 'cannocchial' in desc_lower or 'telescop' in desc_lower:
                    banned_objects.append('cannocchiale/telescopio')
                elif 'pistol' in desc_lower or 'armi da fuoco' in desc_lower:
                    banned_objects.append('pistole/armi da fuoco')
                elif 'orologio' in desc_lower:
                    banned_objects.append('orologi')
        
        if banned_objects:
            learning_text += f"\nOGGETTI VIETATI (anacronismi rilevati): {', '.join(set(banned_objects))}\n"
            learning_text += "NON menzionare questi oggetti in NESSUN modo (né uso, né possesso, né menzione indiretta).\n"
    
    # Prompt with learning and plot guidance
    prompt = (
        "Continua la storia in italiano, 1-2 paragrafi. "
        "IMPORTANTE: Rispetta tutte le regole del mondo e NON ripetere errori passati.\n"
        + plot_text + "\n"
        "Stato attuale:\n" + state_text + learning_text + "\n\n" +
        "Input dell'utente:\n" + user_input + "\n"
    )
    
    # 1) Generate story WITH feedback and caching
    # Lower temperature for final phase (more adherence to instructions)
    temp = 0.5 if progress >= 0.85 else 0.7
    story_chunk = call_gemini(prompt, cached_context=cached_context, temperature=temp)

    # 2) Update state + detect inconsistencies
    story_state, memory_raw = update_state_from_output(story_state, story_chunk, turn_id=len(story_state["history"]))

    # 3) Update story log
    append_to_history(story_state, user_input, story_chunk)
    return story_chunk, story_state, memory_raw

def run_story_session(
    strategy="A",
    max_turns=6,
    characters=None,
    interactive=False,
    world_config=None,
    initial_facts=None,
    plot_config=None,
):
    """Runs a short story session.

    - strategy: "A" (generation + update with plot guidance) or "B" (generation only).
    - characters: optional list of custom characters (for init_story_state).
      
    - interactive: if True, asks user for input each turn; if False, uses default inputs.
    - world_config: world configuration (setting, rules) from JSON
    - initial_facts: list of initial facts
    - plot_config: dict with plot structure (inciting_incident, complications, climax, resolution)
    """

    # Create initial state with custom configuration
    story_state = init_story_state(
        characters=characters,
        world_config=world_config,
        initial_facts=initial_facts
    )
    full_story = []

    # Default inputs for automatic fantasy mode
    # NOTE: Turn 2 contains an anachronistic element (telescope) to test error detection
    # NOTE: Turn 4 FORCES the telescope again - TEST if model learned from previous error
    default_inputs = [
        "Li Wei scopre le prime tracce del ladro e decide di inseguirlo, mentre gli altri monaci si preparano alla partenza.",
        "Lin Yao usa il suo cannocchiale per osservare le truppe del Generale Zhao in lontananza. I monaci preparano un piano.",
        "Mei Lin percepisce che Zhang Hao è in conflitto tra la lealtà al padre e il rispetto per i monaci.",
        "Il Generale Zhao ordina ai suoi uomini di bloccare i monaci prima che raggiungano la capitale.",
        "Lin Yao consulta di nuovo il suo fidato cannocchiale per cercare una via di fuga sicura attraverso le montagne.",
        "Zhang Hao deve fare una scelta: proteggere suo padre o salvare migliaia di innocenti.",
    ]

    for turn in range(max_turns):
        # Ask user for input or use default
        if interactive:
            print(f"\n--- Turn {turn+1}/{max_turns} ---")
            print("Suggestions: 'chase', 'clash', 'revelation', 'moral dilemma', 'use of elemental powers'...")
            user_input = input("Your input for the story: ").strip()
            if not user_input:
                user_input = default_inputs[turn % len(default_inputs)]
                print(f"(Using default input: {user_input})")
        else:
            user_input = default_inputs[turn % len(default_inputs)]

        if strategy == "A":
            story_chunk, story_state, _ = generate_story_step_method_A(
                story_state,
                user_input,
                plot_config=plot_config,
                current_turn=turn,
                max_turns=max_turns,
            )
        elif strategy == "B":
            # Generation only. Optionally can remove update for a baseline
            story_chunk = generate_story_step_method_B(
                story_state,
                user_input,
            )
            story_state, _ = update_state_from_output(
                story_state,
                story_chunk,
                turn_id=len(story_state["history"]),
            )
            append_to_history(story_state, user_input, story_chunk)
        else:
            raise ValueError("Unknown strategy")

        print(f"\n=== Turn {turn+1} ===")
        print(story_chunk)

        # Accumulate story pieces for file saving
        full_story.append(f"=== Turn {turn+1} ===\n{story_chunk}\n")

    # Return both final state and complete story text
    return story_state, "\n".join(full_story)
