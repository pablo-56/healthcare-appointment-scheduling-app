ANNUAL_PHYSICAL = {
  "$schema":"http://json-schema.org/draft-07/schema#",
  "title":"Annual Physical Intake",
  "type":"object",
  "required":["first_name","last_name","dob","phone","address","allergies","medications","insurance"],
  "properties":{
    "first_name":{"type":"string","minLength":1},
    "last_name":{"type":"string","minLength":1},
    "dob":{"type":"string","format":"date"},
    "phone":{"type":"string"},
    "address":{"type":"string"},
    "allergies":{"type":"string"},
    "medications":{"type":"string"},
    "insurance":{"type":"object","required":["payer","member_id"],"properties":{
      "payer":{"type":"string"},
      "member_id":{"type":"string"},
      "group":{"type":["string","null"]}
    }}
  }
}

DEFAULT_INTAKE = {
  "$schema":"http://json-schema.org/draft-07/schema#",
  "title":"General Intake",
  "type":"object",
  "required":["first_name","last_name","dob","phone"],
  "properties":{
    "first_name":{"type":"string","minLength":1},
    "last_name":{"type":"string","minLength":1},
    "dob":{"type":"string","format":"date"},
    "phone":{"type":"string"}
  }
}
# (tiny “per-reason” JSON Schemas)

def schema_for_reason(reason: str):
    r = (reason or "").lower()
    if "annual" in r and "physical" in r:
        return ANNUAL_PHYSICAL
    return DEFAULT_INTAKE
