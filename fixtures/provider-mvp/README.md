# Standard Provider MVP Corpus

This fixture is the small deployment-proof corpus for MCP/OpenAI/Ollama provider
workflows. It is intentionally separate from the full machine corpus so CI and
deployment smoke tests can prove provider wiring without loading every machine.

The fixture contains:

- `provider_observe_probe.json` - read-only/observe trigger metadata.
- `provider_completion_writeback_probe.json` - completion write-back metadata
  for OpenAI, Ollama/localAI, and MCP provider paths.
- `source-mappings.json` - source mappings expected by the provider fixtures.

Provider completions must return through PE via `/api/integrations/completions`.
The fixture must not require live OpenAI, Ollama, OpenClaw, or MCP services.
