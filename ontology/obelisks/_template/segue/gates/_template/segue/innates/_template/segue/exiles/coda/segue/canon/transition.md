# coda segue transition

## status

active

## owner

coda

## singular purpose

coda performs controlled durable mutation of the savant filesystem.

coda is the filesystem mutation boundary through which savant may create or replace durable implementation state without giving mutation ownership to the requesting exile.

## palaver to coda

palaver owns conversation execution.

palaver may request a filesystem mutation from coda.

coda owns the mutation itself.

the active mutation operation is:

- `replace_text`

delegation from palaver to coda does not transfer filesystem mutation authority to palaver.

## mutation pipeline

the mutation pipeline is composed as:

1. palaver establishes an authorized mutation request.
2. the coda palaver bridge validates the request shape.
3. coda resolves the requested path beneath `/root/savant-runtime`.
4. coda rejects paths outside the savant root or inside protected implementation directories.
5. coda calculates the current target digest when the target exists.
6. when an expected digest is supplied, coda requires it to match the current target digest.
7. coda writes the replacement content to a temporary file in the target directory.
8. coda flushes the temporary file before replacement.
9. coda atomically replaces the target.
10. coda calculates the resulting sha256 digest.
11. coda requires the resulting digest to equal the intended content digest.
12. coda emits a durable mutation receipt recording the operation and its provenance.
13. coda returns the mutation projection to palaver.

## concurrency

coda supports optimistic concurrency through `expected_digest`.

a caller that inspected a file before requesting mutation may provide the observed digest.

if the durable file changed between inspection and mutation, coda rejects the operation rather than silently overwriting the newer state.

## durability

successful coda replacement uses same-directory temporary storage followed by atomic replacement.

successful mutation is followed by digest verification.

mutation receipts are stored beneath:

`vault/coda/mutation_receipts`

## authority

filesystem mutation is not authority mutation.

a successful coda write does not, by itself:

- create canon;
- create an accepted decision;
- admit evidence;
- supersede existing authority;
- transfer ownership;
- establish truth.

higher authority mechanisms remain responsible for those effects.

## ownership invariant

the composed pipeline preserves these ownership boundaries:

- conversation: palaver
- filesystem mutation: coda

composition, invocation, projection, and delegation do not imply authority inheritance or authority transfer.
