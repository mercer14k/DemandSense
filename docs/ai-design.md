# Local AI with a narrow job

The LLM explains computed evidence and parses a proposed scenario. It never calculates demand, interval bounds, metrics, workflow state, SQL, or shell commands. There are no AI tools that directly mutate planning state.

## Choice of model

The UI defaults to **AI off · deterministic**. `GET /api/v1/models` discovers installed models through Ollama `/api/tags` and local OpenAI-compatible `/v1/models`. The user chooses a runtime/model for each explanation or draft. No model is selected automatically, bundled, pulled, or downloaded.

Native defaults:

- `OLLAMA_URL=http://127.0.0.1:11434`
- `OPENAI_LOCAL_URL=http://127.0.0.1:8080` (base URL, without `/v1`)

The protocol named `openai-local` is a wire format used by open-source llama.cpp/vLLM servers; it is not an OpenAI cloud integration. Public cloud hosts fail the local host allowlist. Redirects and environment HTTP proxies are disabled. Ollama cloud tags and remote metadata are rejected; start Ollama with `OLLAMA_NO_CLOUD=1` as additional protection.

In Compose, the API uses `host.docker.internal` to reach host inference. Docker-to-host access depends on how the runtime binds its interface. A loopback-only Ollama service may not be reachable from a Linux container; retain native mode or configure a private, firewall-restricted host/container runtime. Do not expose an unauthenticated inference server to a public network. The no-AI workflow requires none of this setup.

## Trust boundary

The adapter implements `LocalRuntime.models()` and `complete()`. Numerical code has no imports from the AI package. Requests use temperature 0, a fixed seed where supported, output limits, a 45-second HTTP timeout, and zero automatic retries. Ollama receives a JSON Schema; compatible servers receive `response_format: json_schema`. Schema support differs by runtime version; unsupported output becomes a safe failure, not a broken forecast.

The prompt labels evidence and scenario text as untrusted data. The response is a Pydantic `Narrative`: summary, citations, abstention flag, and caveats. Unknown evidence IDs, missing non-abstained claims, unknown fields, malformed JSON, and runtime failures yield a deterministic evidence template. Missing evidence causes explicit abstention. Scenario parsing requires explicit uplift/start/end fields, rejects invalid ranges, returns a draft, and needs a separate human Apply action.

**Schema validity and valid citation IDs do not prove semantic truth.** A local model can still misinterpret valid evidence or invent prose. The UI labels AI narrative, shows its citations next to authoritative numbers, and never writes that narrative into model outputs. No private hidden reasoning is requested, consumed, or recorded; Ollama thinking is disabled for this task.

## Observable evaluation

`python scripts/benchmark_ai.py --list` lists discoverable models. For each installed model:

```sh
python scripts/benchmark_ai.py --runtime ollama --model qwen3:8b --repeats 1 --output docs/benchmarks/local-ai.json
```

Use the model name returned by your own runtime; qwen3:8b is an example, not a requirement. Compare runtimes by repeating the command with `--runtime openai-local --model <installed-id>`.

The committed example records a real local run, including digest, latency, token counts, citation count, and a hash assertion that the deterministic run did not change. It is a protocol/failure-isolation benchmark, not a human-rated faithfulness benchmark. The model's own license governs use and redistribution. Never assume that every downloadable weight is open source or permissively licensed.
