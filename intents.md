## greeting
Definition: the user opens with a hello/greeting and no actual task yet.
NOT this: if there's a greeting AND a request ("hi bro mera order kahan hai"),
          it takes the request's intent, not greeting. The task wins.

## talk_to_agent
Definition: the user explicitly asks to be handed to a human / live agent.
NOT this: angry venting ("this app is useless") is `complaint`, even if furious —
          unless they actually ask for a person. The request for a human is the trigger.