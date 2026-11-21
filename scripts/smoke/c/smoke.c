#include <cccr/bindings/c/cccr.h>

#include <stdio.h>

int main(void) {
  const char* version = cccr_version();
  cccr_context* ctx = cccr_context_create();
  if (version == 0 || version[0] == '\0' || ctx == 0) {
    fprintf(stderr, "cccr C library failed to load\n");
    return 1;
  }
  printf("%s\n", version);
  cccr_context_destroy(ctx);
  return 0;
}
