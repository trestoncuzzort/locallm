method Abs(x: int) returns (r: int)
  ensures (r >= 0)
  ensures ((r == x) || (r == (-x)))
{
  if (x < 0) {
    r := (-x);
  } else {
    r := x;
  }
}
