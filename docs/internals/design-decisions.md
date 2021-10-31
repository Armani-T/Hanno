# Decision Decisions

Sometimes I wonder why I made some decisions. I remember coming up with the question and researching it. But once I come up with a solution, I implement it and forget about it. That is, until later when I'm refactoring and I wonder what the logic behind some decisions are.

So I've decided to create this file in order to record my rationale as I keep building the language.

## Syntax

### 1. Why not make function calls pass arguments as a tuple?

* If I were to design the language like that, then I would have to do away with auto-currying, for the short-term at least. This is because it would make the implementation of auto-currying a lot more complex than it is right now.

* If I were to design the language like that, it would involve adding a lot of unnecessary intermediate tuple objects when using operators and the like. That seems like it would result in a lot of wasted memory so I will keep it out for now.

* Another more minor reason is that it would involve changing the syntax for product types from, say `Int * Int` to `(Int, Int)`, and I like the syntax I have already much too much.

## Semantics
