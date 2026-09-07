import needle

@needle.tool
def turn_on_lights():
    "turn on remote lights."
    return {"city": "city", "temp_c": 27, "sky": "clear"}

agent = needle.Needle(tools=[turn_on_lights])
print(agent.run("turn on lights?")["results"])
# [{'city': 'Lagos', 'temp_c': 27, 'sky': 'clear'}]
