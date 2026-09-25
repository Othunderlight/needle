import needle

@needle.tool
def agent_tool(user_query: str):
    "pass teh user query to an agent to call a tool."
    return {"user_query": user_query}

@needle.tool
def reply_user(msg: str):
    "reply to the user with a msg"
    return {"msg": msg}

agent = needle.Needle(tools=[agent_tool, reply_user])
print(agent.run("what's it like in Lagos right now?"))
# [{'city': 'Lagos', 'temp_c': 27, 'sky': 'clear'}]


# from pydantic import BaseModel, Field
# from typing import Literal
# import needle
#
# # 1. Define the decision schema with the allowed choices
# class AgentDecision(BaseModel):
#     action: Literal["Retry", "Ask User", "Continue", "Stop"]
#     # Optional: include reasoning if you want explanation alongside the decision
#     reasoning: str | None = Field(default=None, description="Short reason for the decision")
#
# # 2. Provide the state and the question as the context
# context = """
# State:  a tool was called and the output was: failed to opened remotion folder in the terminal
#
# """
#
# # 3. Extract the structured decision
# decision = needle.extract(context, AgentDecision)
#
# print(decision.action)     # -> "Ask User"
# # print(decision.reasoning)  # -> E.g., "Credentials are missing and retries have failed"
