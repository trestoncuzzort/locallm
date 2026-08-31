method Max(x: int, y: int) returns (r: int)
  ensures (r >= x)
  ensures (r >= y)
  ensures ((r == x) || (r == y))
{
  r := x;
}
