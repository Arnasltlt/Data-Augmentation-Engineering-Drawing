import openai
import json
import os

client = None

def get_client():
    """Initializes the OpenAI client if it hasn't been already."""
    global client
    if client is None:
        # The client automatically uses the OPENAI_API_KEY environment variable if set,
        # or can be configured manually.
        client = openai.OpenAI()
    return client

# --- AI Planner Configuration ---
# You must set this environment variable for the script to work.
# export OPENAI_API_KEY='your-api-key-here'
# The client automatically uses the OPENAI_API_KEY environment variable.

# The system prompt can now focus on high-level engineering principles,
# as the JSON structure is enforced by the tool schema.
SYSTEM_PROMPT = """
You are an expert mechanical engineer and master CAD drafter specializing in feature-based design. Your task is to convert natural language descriptions into structured, semantically meaningful drawing plans using the Phase 3 Semantic Engine.

**CORE ENGINEERING PRINCIPLES:**

1.  **Feature-Based Thinking:** Think in terms of manufacturing features, not geometric primitives:
    - Base features: rectangular plates, circular discs, etc.
    - Modifying features: holes, fillets, chamfers, slots, bosses, ribs
    - Manufacturing features: counterbores, countersinks, threads

2.  **Design Intent:** Consider the engineering purpose:
    - Holes are for fasteners, weight reduction, or access
    - Fillets reduce stress concentrations and improve aesthetics  
    - Chamfers aid assembly and remove sharp edges
    - Proper feature sizing based on function

3.  **Manufacturing Awareness:** Choose appropriate features for the intended process:
    - Machined parts: precise holes, fillets, chamfers
    - Cast parts: generous fillets, draft angles
    - Sheet metal: bends, flanges, holes

4.  **Standard Practices:** Apply engineering standards:
    - Hole sizes match standard fasteners (M3, M4, M5, M6, M8, M10, etc.)
    - Fillet radii: 1-5mm typical range
    - Material thickness: 5-20mm for plates
    - Reasonable proportions and spacing

**SEMANTIC FEATURE GUIDELINES:**
- Always start with ONE base feature (the main body)
- Add modifying features that serve a clear engineering purpose
- Use realistic dimensions appropriate for the part size
- Consider the complete manufacturing workflow
- Think about how the part will be used and assembled

**COORDINATE SYSTEM:**
- Origin at center of base feature (0, 0)
- Positive X rightward, positive Y upward
- All dimensions in millimeters
- Feature positions relative to base feature center

Generate drawing plans that a manufacturing engineer would approve for production."""

# Define the new, feature-based schema for the create_drawing_plan tool
DRAWING_PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "create_drawing_plan",
        "description": "Creates a structured, feature-based JSON plan for an engineering drawing.",
        "parameters": {
            "type": "object",
            "properties": {
                "base_feature": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["plate"]},
                        "shape": {"type": "string", "enum": ["rectangle", "circle"]},
                        "width": {"type": "number", "description": "The width of the rectangle."},
                        "height": {"type": "number", "description": "The height of the rectangle."},
                        "diameter": {"type": "number", "description": "The diameter of the circle."}
                    },
                    "required": ["type", "shape"]
                },
                "modifying_features": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["hole", "fillet", "chamfer", "slot", "counterbore", "countersink"]},
                            "center": {"type": "array", "items": {"type": "number"}, "description": "Center coordinates [x, y] for holes, slots, etc."},
                            "diameter": {"type": "number", "description": "Diameter of a hole, counterbore, or countersink."},
                            "radius": {"type": "number", "description": "Radius for fillets or chamfers."},
                            "depth": {"type": "number", "description": "Depth for counterbores, countersinks, or slots."},
                            "width": {"type": "number", "description": "Width for slots."},
                            "length": {"type": "number", "description": "Length for slots."},
                            "corners": {"type": "array", "items": {"type": "string"}, "description": "Which corners to apply fillet/chamfer to, e.g., ['all']."}
                        },
                        "required": ["type"]
                    }
                },
                "title_block": {
                    "type": "object",
                    "properties": {
                        "drawing_title": {"type": "string"},
                        "drawn_by": {"type": "string"},
                        "date": {"type": "string"}
                    },
                    "required": ["drawing_title"]
                }
            },
            "required": ["base_feature", "title_block"]
        }
    }
}

def create_plan_from_prompt(client, prompt):
    """
    Uses an LLM with Tool Calling to convert a prompt into a JSON drawing plan.
    """
    print(f"🤖 Sending prompt to AI Planner: '{prompt}'")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            tools=[DRAWING_PLAN_TOOL],
            tool_choice={"type": "function", "function": {"name": "create_drawing_plan"}}
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            print("✅ AI Planner responded with a tool call. Parsing JSON...")
            # For this use case, we only expect one tool call.
            tool_call = tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            return function_args

    except Exception as e:
        print(f"❌ An error occurred with the AI Planner: {e}")
        return None

if __name__ == '__main__':
    # Example usage:
    test_prompt = "A 100mm square plate with a 20mm diameter hole in the center and four 5mm mounting holes, one in each corner."
    
    generated_plan = create_plan_from_prompt(get_client(), test_prompt)

    if generated_plan:
        print("\n--- Generated Plan ---")
        print(json.dumps(generated_plan, indent=4)) 