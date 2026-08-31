/*@
  ensures (\result >= 0);
  ensures ((\result == x) || (\result == (-x)));
*/
int abs_t(int x) {
  return (-x);
}
