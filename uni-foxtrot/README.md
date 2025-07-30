# UNI Phase Foxtrot

**Phase Foxtrot** marks a major milestone in the evolution of the Universal Neural Intelligence Engine (UNI). Building on the linguistic foundations of Phase Echo, this phase introduces **deep syntactic parsing** using full dependency and constituency trees. For the first time, UNI can understand hierarchical grammatical relationships, not just flat sentence structures.

This phase enables UNI to:
- Precisely recognize sentence structure using dependency parsing
- Identify grammatical relationships between words (subject, verb, object, modifiers)
- Map hierarchical trees into deterministic phrase roles
- Begin **self-learning** by analyzing new input structures and adapting internal phrase representations

---

## 🔧 How to Run

This phase requires a separate syntactic parsing service to be running, powered by the [Stanza](https://stanfordnlp.github.io/stanza/) pipeline.

### Start the Stanza Service

Instead of calling Stanza inline for every input (which is slow), this phase runs a persistent service that responds to HTTP requests:

```bash
py -m helpers.stanza
```