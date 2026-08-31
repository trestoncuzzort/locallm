use vstd::prelude::*;

verus! {

proof fn max(x: int, y: int) -> (r: int)
    ensures
        (r >= x),
        (r >= y),
        ((r == x) || (r == y)),
{
    x
}

} // verus!

fn main() {}
