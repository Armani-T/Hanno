# Syntax Overview

This is a quick and dirty tour of the syntax in Hanno. It is intended to help experienced programmers or people who just want to have a look around get a feel of the language.

## Comments

```
# This is a line comment.

#==
This
is
a
block
comment
.
==#
```

There are also *docomments* which are used for documentation. By convention, they are look like this:

```
#| This is a single line that explains something.

#==
| This docomment
| takes multiple
| lines to
| explain something.
==#
```

## Literals

The following literal types are supported in the language:

```
False   # Bool
42      # Int
3.142   # Float
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

You can group things together to make stuff more understandable. These are called tuples and they are made by surrounding the things with parentheses (`(` and `)`) then putting commas between them. They look like this:

```
(1, 2, 3)
("Hello", "World", 123)
(True, 3.14)
```

Tuples can have any number of elements except 1. A tuple with only 1 element will simply evaluate to that 1 element.

A tuple with 0 elements is called a *unit*. It has the type `Unit`. It's usually returned by functions which don't have a useful return value.

The type of a tuple is the product of the types of its elements. This is why tuples can't have only a single element. Since their types are products, if there is only 1 type then you can't do any multiplication.

```
let origin: Int * Int * Int = (0, 0, 0)
```


## Lists

Hanno has only 1 other sequence type: the `List`. `List` is a general-purpose homogenous (i.e. all elements have to be of the same type) sequence based on a linked list.

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
You can choose to declare the type of a name by putting a `:` and the type between the name and the `=` like so:

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

And anonymous functions (a.k.a. _lambdas_) are defined like so:

```
\x, y -> to_int(x) + to_int(y)
```

Functions can be called by wrapping the arguments passed in parentheses and the arguments are separated by commas.

```
poly_add("12", "24")
```

### Operators

We have all the common mathematical and logical operators from other programming languages. In order of precedence, they are:

- `and`
- `or`
- `not`
- `>`, `<`, `>=`, `<=`, `=`, `/=`
- `+`, `-` (binary subtraction), `<>`
- `/`, `*`, `%`
- `^`
- `-` (unary negation)
- `()` (function call)

About the operators themselves:

- `and`, `or` and `not` are operate on `Bool`s. They are the usual operators from Boolean algebra.
- `>`, `<`, `>=`, `<=`, `=` and `/=` are the comparison operators.
- `+`, `-`,`*`, `/`, `%` and `^` are the usual arithmetic operators.
- `.` is not the usual OOP attribute access operator. It is actually just syntactic sugar for a function call.

### Conditionals

The conditional expression in Hanno is used to choose which of 2 or more code sections will be run. The first condition section of an `if` must evaluate to a `Bool`. Since `if` is an expression, an `else` section *must* be present.

```
let letter_grade = (
    if marks >= 75 then "A"
    else if marks >= 65 then "B"
    else if marks >= 55 then "C"
    else if marks >= 40 then "D"
    else "E"
)
```

Like in most programming languages, `if` short-circuits (it can run only 1 branch at most).
