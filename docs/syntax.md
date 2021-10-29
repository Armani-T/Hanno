# Syntax Overview

This is a quick and dirty tour of the syntax in Hasdrubal. It is intended to help experienced programmers or people who just want to have a look around get a feel of the language.

## Comments

```
# Single line comment

###
Multi
line
comment
###
```

There are also *docomments* which are used for documentation. By convention, they are made like this:

```
#| This is a single line that explains something.

###
| This docomment
| takes multiple
| lines to
| explain something.
###
```

## Literals

Hasdrubal supports the usual kinds of literals: `Bool`s, `Int`s, `String`s and `Float`s.

```
False   # Bool
42      # Int
3.141   # Float
"text"  # String

"
strings
can
be
more
than
one
line
long
"
```

## Tuples

You can group things together to make stuff more understandable. These are called tuples and they are made by surrounding the things with `(` and `)` then adding commas between them. They look like this:

```
(1, 2, 3)
("Hello", "World", 123)
(True, 3.14)
```

Tuples can have any number of elements, except 1. A tuple with only 1 element will evaluate to that 1 element.

A tuple with 0 elements is called a unit. It has the type `Unit`. It's usually returned by functions where you don't care about the return value.

The type of a tuple is the product of the types of its elements. This is why tuples can't have only a single element. They are _product_ types and there is no multiplication when there's only 1 type.

```
let origin: (Int * Int * Int) = (0, 0, 0)
```


## Lists

Hasdrubal has only 1 sequence type: the `List`. `List` is a general purpose sequence type which must have elements of only 1 type.

```
[0, 1, 1, 2, 3]      # List[Int]
[True, True, True]   # List[Bool]
[]                   # List[a]
```

## Definitions

These allow us to bind a value to a name.

```
let meaning_of_life = 42
```
You can choose to declare the type of a name by putting a `:` and the type just before the `=`, like this:

```
let meaning_of_life: Int = 42
```

## Flow Control

### Functions

Functions are defined using more or less the same syntax as normal definitions:

```
let plus_1(n) = n + 1
```

Functions can also have blocks as a body:

```
let keep_n(seq, n) :=
    #| Keep every n'th item from seq and remove all the others.

    let distance = length(seq) / n
    let indexes = range(0, 1, length(seq) + 1)
    let return = [
        at(index, seq)
        | index % distance = 0
        | index <- indexes
    ]
end
```

Anonymous functions (a.k.a. _lambdas_) are defined like so:

```
\x, y -> to_int(x) + to_int(y)
```

Functions can be called by wrapping the arguments passed in parentheses and the arguments are separated by commas.

```
poly_add("12", "24")
```

### Operators

Hasdrubal has the usual built-in mathematical and logical operators of other programming languages. In order of precedence, they are:

- `|>`
- `and`
- `or`
- `not`
- `>`, `<`, `>=`, `<=`, `=`, `/=`
- `+`, `-` (binary subtract), `<>`
- `/`, `*`, `%`
- `^`
- `-` (unary negation)
- `()` (function call)
- `.` (function call)

`and`, `or` and `not` are operate on `Bool`s. They are the usual operators from Boolean algebra.

`>`, `<`, `>=`, `<=`, `=` and `/=` are the comparison operators.

`+`, `-`,`*`, `/`, `%` and `^` are the usual arithmetic operators.

`|>` and `.` are operators that takes the value on the left and passes it to the function on the right. As an example, these 3 styles are all equivalent:

```
12 |> to_string
12.to_string
to_string(12)
```

### Conditionals

The conditional expression in Hasdrubal is used to choose which of 2 or more code sections will be run. The first condition section of an `if` must evaluate to a `Bool` and if it doesn't, the compiler will flag a type error. Since `if` is an expression, the `else` section *must* be present and if it isn't, the compiler will flag it as a parsing error.

```
let letter_grade = (
    if marks >= 75 then "A"
    else if marks >= 65 then "B"
    else if marks >= 55 then "C"
    else if marks >= 40 then "D"
    else "E"
)
```

Like in most programming languages, `if` short-circuits (it only ever runs one branch).
