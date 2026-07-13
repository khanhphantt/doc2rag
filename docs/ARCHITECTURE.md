[//]: # (TODO: Write architecture document)

*Below are guidelines to write Architecture.md files based on [this guide](https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html).
Feel free to adapt them to your situation and don't forget to remove this when adding the architecture.*

One of the biggest difference between an occasional contributor and a core developer  lies in the knowledge about the 
physical architecture of the project. Roughly, it takes 2x more time to write a patch if you are unfamiliar with the 
project, but it takes 10x more time to figure out where you should change the code. 
This difference might be hard to perceive if you’ve been working with the project for a while. A developer new to a code 
base will each file as a sequence of logical chunks specified in some pseudo-random order. Once they've made significant 
contributions before, the perception is quite different. They have a mental map of the code in their head, so they no 
longer read sequentially. Instead, they just jump to where the thing should be, and, if it is not there, they move it. 
One’s mental map is the source of truth.

The ARCHITECTURE file to be a low-effort high-leverage way to bridge this gap. As the name suggests, this file 
should describe the high-level architecture of the project. 

- **Keep it short.** Every recurring contributor will have to read it. 
Additionally, the shorter it is, the less likely it will be invalidated by some future change. 
This is the main rule of thumb for ARCHITECTURE — only specify things that are unlikely to frequently change. 
Don’t try to keep it synchronized with code. Instead, revisit it a couple of times a year.

- **Start with a bird’s eye overview** of the problem being solved. Then, specify a more-or-less detailed codemap. 
Describe coarse-grained modules and how they relate to each other. The codemap should answer “where’s the thing that 
does X?”. It should also answer “what does the thing that I am looking at do?”. 
Avoid going into details of how each module works, pull this into separate documents or (better) inline documentation. 
A codemap is a map of a country, not an atlas of maps of its states. Use this as a chance to reflect on the 
project structure. Are the things you want to put near each other in the codemap adjacent when you run `tree .`?

- **Do name important files, modules, and types.** Do not directly link them (links go stale). 
Instead, encourage the reader to use symbol search to find the mentioned entities by name. This doesn’t require 
maintenance and will help to discover related, similarly named things.

- **Explicitly call-out architectural invariants.** Often, important invariants are expressed as an absence of 
something, and it’s pretty hard to divine that from reading the code. Think about a common example from web development:
nothing in the model layer specifically doesn’t depend on the views.

- **Point out boundaries between layers and systems as well.** A boundary implicitly contains information about the 
implementation of the system behind it. It even constrains all possible implementations. But finding a boundary by just
randomly looking at the code is hard — good boundaries have measure zero.

After finishing the codemap, add a separate section on cross-cutting concerns.

A good example of ARCHITECTURE document is this one from rust-analyzer: [architecture.md](https://github.com/rust-analyzer/rust-analyzer/blob/d7c99931d05e3723d878bea5dc26766791fa4e69/docs/dev/architecture.md).