/*@
  assigns \nothing;
  ensures (\result >= x);
  ensures (\result >= y);
  ensures ((\result == x) || (\result == y));
*/
int max_t(int x, int y) {
  int r;
  if ((x >= y)) {
    r = x;
  } else {
    r = y;
  }
  return r;
}
