# Hasdrubal README

[![License](https://img.shields.io/github/license/Naereen/StrapDown.js.svg)](https://github.com/Naereen/StrapDown.js/blob/master/LICENSE) [![Build Status](https://travis-ci.com/Armani-T/hasdrubal.svg?branch=main)](https://travis-ci.com/Armani-T/hasdrubal) [![codecov](https://codecov.io/gh/Armani-T/hasdrubal/branch/main/graph/badge.svg?token=AJVzAMeQAP)](https://codecov.io/gh/Armani-T/hasdrubal) [![Updates](https://pyup.io/repos/github/Armani-T/hasdrubal/shield.svg)](https://pyup.io/repos/github/Armani-T/hasdrubal/) [![Python 3](https://pyup.io/repos/github/Armani-T/hasdrubal/python-3-shield.svg)](https://pyup.io/repos/github/Armani-T/hasdrubal/)

```
|-|   |-|                      |-|                  |-|              |-|
| |   | |                      | |                  | |              | |
| |___| |                      | |                  | |              | |
| _____ |   ____  +-----|   ___| | |-|____ |-|  |-| | |___     ____  | |
| |   | |  / _  | | ----+  / __  | | +---- | |  | | |  _  \   / _  | | |
| |   | | | (_| | +____ | | (__| | | |     | |__| | | |_)  | | (_| | | |
|_|   |_|  \__,_| |_____|  \_____| |_|     |____,_| |_____/   \__,_| |_|
```

A general-purpose functional programming language built around making algebraic effects practical.

Algebraic effects are a new method of adding impurity to purely functional languages using continuations. In practice, they act like exceptions in imperative languages but you can use them for anything from I/O to mutable state to regular exceptions.

### Features

The language should have (at least) these features:

- [X] First class functions
- [ ] Algebraic Data Types
- [ ] Rust-style traits
- [X] Hindley-Milner type inference
- [ ] Algebraic effect inference
- [ ] An OCaML-style module system

## Installation

Here's how to get it on your machine:

```bash
git clone https://github.com/Armani-T/hasdrubal
cd hasdrubal
```

At the moment, the language is not fully implemented so it cannot run any code but that will change very soon.

You can check if it's working by running `python hasdrubal --version`. If it installed properly, it should print out `Hasdrubal Version 0.0.1`. Another way to check if it's running by running the test suite with `pytest` (first ensure that you have installed the testing framework by running `pip install -r requirements-test.txt`).

## Development Setup

Just follow the above steps but before working on the code also run:

```bash
pip install -r requirements-dev.txt
```

After that, check if it's fully functional by running the tests with:

```bash
pytest
```

## Contributing

Please use GitHub issues for bug reports and feature requests.

1. Create your feature branch by forking the `develop` branch.
3. Commit your changes.
4. Push to `origin/develop`.
5. Open a pull request.

## Notes

- I'm currently working on a python implementation which will serve as the reference implementation.
- A future Rust implementation is planned. It will be more focused on speed.

## Meta

- Name: **Armani Tallam**
- E-Mail: armanitallam@gmail.com
- GitHub: <https://www.github.com/Armani-T>

This project is licensed under the **MIT License**. Please see [the license file](LICENSE) for more info on the licensing.
