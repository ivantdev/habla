import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import schema from "../../contracts/v1.json" with { type: "json" };

const validator = new Ajv({ strict: false });
addFormats(validator);
validator.addSchema(schema);

export function conforms(name, value) {
  return validator.getSchema(`${schema.$id}#/$defs/${name}`)(value);
}
