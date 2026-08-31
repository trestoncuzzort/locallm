use vstd::prelude::*;

verus! {

proof fn max(x: int, y: int) -> (r: int)
    ensures
        (r >= x),
        (r >= y),
        ((r == x) || (r == y)),
{
    if (x >= y) { x } else { y }
}

} // verus!

fn main() {}
