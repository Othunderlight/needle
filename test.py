from ollama import chat
from pydantic import BaseModel

# class Pet(BaseModel):
#   name: str
#   animal: str
#   age: int
#   color: str | None
#   favorite_toy: str | None

# class PetList(BaseModel):
#   pets: list[Pet]

response = chat(
  model='ibm/granite4:350m',
  messages=[
      {'role': 'system', 'content': 'your job is to take a tool ouput and will convert it to a userfull feedback for the non technical user, i will send it to the users directlyy, so give me the ready oneliner without any more explination'},
      {'role': 'user', 'content': "the user asked to 'open the files'  here is the tool output, go ahead: {'success': True, 'error': None, 'results': ['Successfully opened ptyxis (ran: `ptyxis --new-window`)']}"}
  ],
  # format=PetList.model_json_schema(),
)

# pets = PetList.model_validate_json(response.message.content)
# print(pets)
print(response.message.content)

