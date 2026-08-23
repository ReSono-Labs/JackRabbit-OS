import Ajv2020 from "ajv/dist/2020.js";

export class ContractError extends Error {
  constructor(code, message, details = []) {
    super(message);
    this.name = "ContractError";
    this.code = code;
    this.details = details;
  }
}

export function createContractValidator(schemas) {
  const ajv = new Ajv2020({ allErrors: true, strict: true });
  for (const schema of schemas) {
    ajv.addSchema(schema);
  }

  return Object.freeze({
    validate(schemaId, value) {
      const validate = ajv.getSchema(schemaId);
      if (!validate) {
        throw new ContractError("JR-RELEASE-SCHEMA", `unknown schema: ${schemaId}`);
      }
      if (!validate(value)) {
        throw new ContractError(
          "JR-RELEASE-SCHEMA",
          "release contract validation failed",
          (validate.errors ?? []).map(({ instancePath, keyword, message }) => ({
            instancePath,
            keyword,
            message
          }))
        );
      }
      return value;
    }
  });
}
