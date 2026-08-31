/*@
  ensures (\result >= 0);
  ensures ((\result == x) || (\result == (-x)));
*/
int abs_t(int x) {
  if (x < 0) {
    return (-x);
  } else {
    return x;
  }
}
