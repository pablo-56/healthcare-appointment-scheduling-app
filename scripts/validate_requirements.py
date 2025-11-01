import json,yaml,jsonschema
with open('requirements.yaml') as f:req=yaml.safe_load(f)
with open('ops/requirements.schema.json') as f: schema=json.load(f)
jsonschema.validate(instance=req, schema=schema)
print('requirements.yaml is valid')
