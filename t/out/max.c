/*@
  ensures (\result >= x);
  ensures (\result >= y);
  ensures ((\result == x) || (\result == y));
*/
int max_t(int x, int y) {
  if (x >= y) {
    return x;
  } else {
    return y;
  }
}
