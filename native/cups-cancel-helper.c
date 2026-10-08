/* Fresh exec boundary for CCPD's CUPS cancellation. No shell or cancel-all. */
#include <cups/cups.h>
#include <errno.h>
#include <limits.h>
#include <pwd.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 3 || !argv[1][0] || !argv[2][0]) return 2;
    char *end;
    errno = 0;
    long job = strtol(argv[2], &end, 10);
    if (errno || *end || job <= 0 || job > INT_MAX) return 2;
    /* The desktop data agent runs as the logged-in user. Claiming "root"
     * makes CUPS reject cancellation of that user's own queued jobs. */
    struct passwd *account = getpwuid(geteuid());
    if (!account || !account->pw_name[0]) return 1;
    cupsSetUser(account->pw_name);
    return cupsCancelJob(argv[1], (int)job) ? 0 : 1;
}
