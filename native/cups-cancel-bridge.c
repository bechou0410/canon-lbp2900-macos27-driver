/* CCPD calls CUPS after fork. Run cancellation in a fresh process so CUPS may
 * initialize CoreFoundation/Objective-C safely; re-export all other CUPS APIs. */
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <spawn.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;
static char helper[PATH_MAX];

__attribute__((constructor)) static void locate_helper(void) {
    Dl_info info;
    char path[PATH_MAX];
    if (!dladdr((void *)&locate_helper, &info) || !realpath(info.dli_fname, path))
        return;
    char *name = strrchr(path, '/');
    if (!name) return;
    size_t directory = (size_t)(name - path) + 1;
    const char suffix[] = "lb29-cancel";
    if (directory + sizeof(suffix) > sizeof(helper)) return;
    memcpy(helper, path, directory);
    memcpy(helper + directory, suffix, sizeof(suffix));
}

static int run_cancel(const char *printer, int job) {
    /* Never turn malformed input into cancel-all or a command-line option. */
    if (!helper[0] || !printer || !printer[0] || job <= 0) return 0;
    char number[12];
    char *digits = number + sizeof(number) - 1;
    *digits = '\0';
    unsigned value = (unsigned)job;
    do { *--digits = (char)('0' + value % 10); value /= 10; } while (value);
    char *args[] = { helper, (char *)printer, digits, NULL };
    posix_spawnattr_t attributes;
    if (posix_spawnattr_init(&attributes)) return 0;
    /* Do not retain CCPD sockets, USB descriptors or synchronization pipes. */
    int error = posix_spawnattr_setflags(&attributes, POSIX_SPAWN_CLOEXEC_DEFAULT);
    pid_t child = -1;
    if (!error) error = posix_spawn(&child, helper, NULL, &attributes, args, environ);
    posix_spawnattr_destroy(&attributes);
    if (error) return 0;

    /* Bound a stalled helper while preserving the real CUPS result. */
    const struct timespec interval = { 0, 100000000 };
    for (unsigned attempt = 0; attempt < 300; ++attempt) {
        int status;
        pid_t result = waitpid(child, &status, WNOHANG);
        if (result == child) return WIFEXITED(status) && WEXITSTATUS(status) == 0;
        if (result == -1 && errno != EINTR) return 0;
        nanosleep(&interval, NULL);
    }
    kill(child, SIGKILL);
    while (waitpid(child, NULL, 0) < 0 && errno == EINTR) {}
    return 0;
}

int cupsCancelJob(const char *printer, int job) {
    /* The single-threaded CCPD data-agent child inherits a SIGCHLD handler
     * that terminates it. Reap our helper without invoking that handler, then
     * restore Canon's disposition for its own children. */
    struct sigaction previous, action = {0};
    action.sa_handler = SIG_DFL;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGCHLD, &action, &previous)) return 0;
    int result = run_cancel(printer, job);
    if (sigaction(SIGCHLD, &previous, NULL)) return 0;
    return result;
}
