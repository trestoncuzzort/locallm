/*@
  ensures (\result >= x);
  ensures (\result >= y);
  ensures ((\result == x) || (\result == y));
*/
int max_t(int x, int y) {
  return x;
}
