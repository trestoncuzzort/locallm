/*@
  assigns \nothing;
  ensures (\result >= 0);
  ensures ((\result == x) || (\result == (-x)));
*/
int abs_t(int x) {
  int r;
  if ((x < 0)) {
    r = (-x);
  } else {
    r = x;
  }
  return r;
}
