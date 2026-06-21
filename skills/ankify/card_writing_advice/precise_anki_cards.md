# Rules for Designing Precise Anki Cards

Source: https://controlaltbackspace.org/precise/

---

## Core Principles

### 1. Ask Exactly One Thing

The "Minimum Information Principle" demands atomic cards. Rather than "Describe Python," create targeted questions like "Who designed Python?" This prevents learners from memorizing vague responses and forces meaningful reflection on what you actually need to know.

### 2. Permit Exactly One Answer

Questions must have an unambiguous correct response.

**Bad example**: A cloze deletion about the Articles of Confederation having no power to regulate "{commerce}" is problematic because infinite technically correct answers exist (religious observances, taxation, etc.).

**Fix**: Rewrite to specify the *reason* commerce regulation mattered, eliminating ambiguity.

### 3. Avoid Enumeration

"Sets" asking you to list items are frustrating and typically unhelpful. "What are parts of an engine?" teaches memorization, not understanding. Instead, learn individual components through separate cards, then optionally use mnemonics for sequences.

### 4. Skip Yes/No Questions

These are harder to retain than richer formats.

**Bad**: "Is segmentation used on modern processors? No"

**Better**: "Segmentation was removed starting with the {{x86-64}} platform"

The second version captures the same knowledge plus useful detail.

### 5. Be Context-Free

Questions must be fully comprehensible independently. Include topic markers ("OutSystems:" or "APUSH:") at the start. Avoid source-dependent framing like "Our textbook says..."—instead ask about ideas *within* sources.

## The Broader Philosophy

"Identify exactly what you want to know" before creating cards. This prevents overfitting—the SRS excels at teaching whatever you encode, whether useful or trivial. The reflection required breeds elaborative encoding, aiding learning before reviews even begin.

## The Anti-Pattern: Overfitting

In a spaced-repetition context, because the SRS is so good at helping you learn things efficiently, it will optimize your memory of just about anything. But if you don't phrase your question correctly, it will help you remember irrelevant information or random noise, rather than the information you actually wanted to know.

To avoid overfitting: every time you come across something you think you'd like to remember, identify exactly what you want to know, and be as precise about it as possible. Then, and only then, create one or more cards that ask about exactly that and nothing else.
