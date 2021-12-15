# The Hasdrubal Language

Hasdrubal is a fairly high-level, statically-typed, general-purpose, compiled functional programming language. Hasdrubal is inspired by a lot of different languages, e.g. F# for the semantics. Like most other functional languages, we have (or intend to have) first-class functions, ADTs, pattern matching and sum types.

Since we are part of the family of functional languages, we also really like code that is side-effect free. Side effects include printing to the console, mutating variables and writing to files. These are all obviously things we still want to do. That presents a problem.

Some languages use monads to allow side effects, but those come with some hard limitations. Others freely allow them but encourage you to be pure, but this can lead to unsafe code since unless you read the source code, you can't be sure that a piece of code won't access a resource it shouldn't.

This is where Hasdrubal comes in. What differentiates Hasdrubal from most other functional languages is the use of *Algebraic Effects* to handle side effects in code. Here is an example of how they work:

## "Hello World" in Hasdrubal

```
# My first program in Hasdrubal.
let main(args) :=
    let message = "Hello, World!"
    print_line(message)
    0
end
```

All executable programs in Hasdrubal have a `main` function. Without `main`, the compiler will assume that any file passed to it is a library so the program won't run.

The `main` function always takes 1 argument (usually called `args`). `args` is a list of the command line arguments passed in to the program from the command line. The `main` function also always returns an `Int`. This `Int` becomes the program's exit status.

You may have noticed that there is no `return` keyword. This is because functions automatically return the value of the last line in the function.

-----

- Get an bird's eye view of the syntax [here](./syntax.md).
- Do a short tutorial on the Hasdrubal [here](./tutorial/installing.md).
- Learn how to contribute contribute to the project over [here](./contributing.md).
