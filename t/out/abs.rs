use vstd::prelude::*;

verus! {

proof fn abs(x: int) -> (r: int)
    ensures
        (r >= 0),
        ((r == x) || (r == (-x))),
{
    if (x < 0) { (-x) } else { x }
}

} // verus!

fn main() {}
