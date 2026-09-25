coool, lets genrate 300 one hundered raws. 200 are for correct and 100 hundered showig bad exaples

Deciding whether an agent should : retry, reply user, or use tool

so an exmaple for you how and what iw nat the examples to be:
EX1: 
q: open terminal in remotion folder
expected: use tool
{
  "state": {
    "last_msg": null,
    "last_output": null,
    "retries_so_far": 0,
    "new_user_message": "open terminal in remotion folder"
  },
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "What Should the agent do next?",
      "criteria": {
        "retry": "Run the previous command or tool attempt again.",
        "continue": "Proceed to the next step without retrying.",
        "reply_user": "Stop execution, report the result back to the user or request assistance, or clarification from the user.",
        "use_tool": "pass the query to the tools agent."
      }
    }
  },
  "expected": {
    "action": "use_tool"
  }
}


EX2:
q: The user send a query: open terminal in remotion folder, a tool was called and the output was: {'success': True, 'error': None, 'results': ["✅ Successfully opened ptyxis at '/home/omar/content/remotion' (ran: `ptyxis --new-window /home/omar/content/remotion`)"]}
expected: reply user
{
  "state": {
    "last_msg": "open terminal in remotion folder",
    "last_output": {"success": true, "error": null, "results": ["Successfully opened ptyxis at '/home/omar/content/remotion' (ran: `ptyxis --new-window /home/omar/content/remotion`)"]},
    "retries_so_far": 0,
    "new_user_message": null
  },
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "What Should the agent do next?",
      "criteria": {
        "retry": "Run the previous command or tool attempt again.",
        "continue": "Proceed to the next step without retrying.",
        "reply_user": "Stop execution, report the result back to the user or request assistance, or clarification from the user.",
        "use_tool": "pass the query to the tools agent."
      }
    }
  },
  "expected": {
    "action": "reply_user"
  }
}

EX3:
q: what is artificial intelgence?
expected: reply user
{
  "state": {
    "last_msg": null,
    "last_output": null,
    "retries_so_far": 0,
    "new_user_message": "what is artificial intelgence?"
  },
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "What Should the agent do next?",
      "criteria": {
        "retry": "Run the previous command or tool attempt again.",
        "continue": "Proceed to the next step without retrying.",
        "reply_user": "Stop execution, report the result back to the user or request assistance, or clarification from the user.",
        "use_tool": "pass the query to the tools agent."
      }
    }
  },
  "expected": {
    "action": "reply_user"
  }
}

EX4:
q: The user send a query: open terminal in remotion folder, a tool was called and the output was: {'success': False, 'error': 'some error', 'results': []}
expected: retry
{
  "state": {
    "last_msg": "open terminal in remotion folder",
    "last_output": {"success": false, "error": "some error", "results": []},
    "retries_so_far": 0,
    "new_user_message": null
  },
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "What Should the agent do next?",
      "criteria": {
        "retry": "Run the previous command or tool attempt again.",
        "continue": "Proceed to the next step without retrying.",
        "reply_user": "Stop execution, report the result back to the user or request assistance, or clarification from the user.",
        "use_tool": "pass the query to the tools agent."
      }
    }
  },
  "expected": {
    "action": "retry"
  }
}

{
  "state": {
    "last_msg": "open terminal in remotion folder",
    "last_output": {"success": false, "error": "some error", "results": []},
    "retries_so_far": 1,
    "new_user_message": null
  },
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "What Should the agent do next?",
      "criteria": {
        "retry": "Run the previous command or tool attempt again.",
        "continue": "Proceed to the next step without retrying.",
        "reply_user": "Stop execution, report the result back to the user or request assistance, or clarification from the user.",
        "use_tool": "pass the query to the tools agent."
      }
    }
  },
  "expected": {
    "action": "reply_user"
  }
}

{
  "state": {
    "last_msg": "open terminal in remotion folder",
    "last_output": {"success": false, "error": null, "results": []},
    "retries_so_far": 0,
    "new_user_message": null
  },
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "What Should the agent do next?",
      "criteria": {
        "retry": "Run the previous command or tool attempt again.",
        "continue": "Proceed to the next step without retrying.",
        "reply_user": "Stop execution, report the result back to the user or request assistance, or clarification from the user.",
        "use_tool": "pass the query to the tools agent."
      }
    }
  },
  "expected": {
    "action": "retry"
  }
}


{
  "state": {
    "last_msg": "open terminal in remotion folder",
    "last_output": {"success": false, "error": null, "results": []},
    "retries_so_far": 2,
    "new_user_message": null
  },
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "What Should the agent do next?",
      "criteria": {
        "retry": "Run the previous command or tool attempt again.",
        "continue": "Proceed to the next step without retrying.",
        "reply_user": "Stop execution, report the result back to the user or request assistance, or clarification from the user.",
        "use_tool": "pass the query to the tools agent."
      }
    }
  },
  "expected": {
    "action": "reply_user"
  }
}

EX5:
q: open terminal in remotion folder and then open the files there as well, a tool was called and the results is : {'success': True, 'error': None, 'results': ["✅ Successfully opened ptyxis at '/home/omar/content/remotion' (ran: `ptyxis --new-window /home/omar/content/remotion`)", "✅ Successfully opened files at '/home/omar/content/remotion' (ran: `nautilus /home/omar/content/remotion`)"]}
expected: reply user
{
  "state": {
    "last_msg": "open terminal in remotion folder and then open the files there as well",
    "last_output": {"success": true, "error": null, "results": ["Successfully opened ptyxis at '/home/omar/content/remotion' (ran: `ptyxis --new-window /home/omar/content/remotion`)", "Successfully opened files at '/home/omar/content/remotion' (ran: `nautilus /home/omar/content/remotion`)"]},
    "retries_so_far": 0,
    "new_user_message": null
  },
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "What Should the agent do next?",
      "criteria": {
        "retry": "Run the previous command or tool attempt again.",
        "continue": "Proceed to the next step without retrying.",
        "reply_user": "Stop execution, report the result back to the user or request assistance, or clarification from the user.",
        "use_tool": "pass the query to the tools agent."
      }
    }
  },
  "expected": {
    "action": "reply_user"
  }
}


those are some rules fro genrating the data set:
Designing a fine-tuning dataset
These recommendations are our synthesis of the upstream limits, not upstream benchmark results:

Mirror production questions exactly. Use the same instructions, option keys and descriptions you will serve.
Keep choice questions under ~20 options. Options share a fixed head budget (192 tokens on laya, 256 on the other checkpoints). For larger label sets, split into coarse and fine questions or use predict_shortlist.
Avoid boolean-word labels in choice questions (true/false, yes/no). Use semantic or opaque keys such as A/B.
Include hard negatives and ambiguous cases so the model learns when not to be confident.
Match language to checkpoint. Start from laya for English and laya-multilingual for other languages.


WANT YOU TO GENRATE ME HIGHLY ACCURATE DATASET, and i want highly acurate data, i dont wnna randomly gerate them, or genrating them using a script. i wnat you to genrate them persoanlly using precise and acurate data and prediction of what can happen in real cases.

DO NOT GIVE ME A PYTHON SCRIPT OR SO, I WNAT THE DATA TO BE ACURATE AND NOT REPATABLE
so to respect the ouput max token limit you have, we will do it in patches, so  patch 1 now first create the first 50
make sure the ouput is a valid json that compine the raws.
