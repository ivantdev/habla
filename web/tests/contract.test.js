import assert from "node:assert/strict";
import test from "node:test";
import examples from "../../contracts/fixtures/platform-v1.json" with { type: "json" };
import { conforms } from "../src/contract.js";

test("el consumidor acepta los ejemplos C-08 del contrato v1", () => {
  assert.equal(examples.contract_version, "1");
  assert.equal(examples.simulation, true);
  assert.ok(conforms("AccountView", examples.account));
  assert.ok(conforms("ConsentRecord", examples.consent));
  assert.ok(conforms("ErrorEnvelope", examples.busy));
  for (const practice of examples.practices) assert.ok(conforms("Practice", practice));
  for (const audio of examples.audio_assets) assert.ok(conforms("AudioAsset", audio));
});

test("el consumidor rechaza estado desconocido, versión ausente y audio inválido", () => {
  const [practice] = examples.practices;
  assert.equal(conforms("Practice", { ...practice, status: "unknown" }), false);
  const { state_version, ...missingVersion } = practice;
  assert.equal(conforms("Practice", missingVersion), false);
  assert.equal(conforms("AudioAsset", { ...examples.audio_assets[0], duration_ms: -1 }), false);
});
