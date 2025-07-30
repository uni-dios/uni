# UNI Phase Charlie

**Phase Charlie** adds persistent memory for parsed inputs by introducing storage of detected phrase structures into the database.

This phase:
- Extracts phrase-level patterns from user input
- Saves parsed tokens, phrase groups, and their relationships into `uni_phrases` and `uni_tokens`
- Enables long-term comparison of user inputs over time

This milestone marks the shift from being reactive to becoming self-aware — UNI starts building a library of known linguistic structures.
