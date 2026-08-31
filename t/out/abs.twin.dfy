method Abs(x: int) returns (r: int)
  ensures (r >= 0)
  ensures ((r == x) || (r == (-x)))
{
  r := (-x);
}
