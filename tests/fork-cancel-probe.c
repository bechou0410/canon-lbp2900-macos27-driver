/* Real system CUPS failure response after fork; never creates a print job. */
#include <CoreFoundation/CoreFoundation.h>
#include <cups/cups.h>
#include <pthread.h>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

static volatile sig_atomic_t termination_requested;
static void child_exit(int signal) { (void)signal; termination_requested = 1; }

static void *worker(void *unused) {
    (void)unused;
    for (;;) pause();
    return NULL;
}

int main(void) {
    CFRunLoopGetCurrent();
    pthread_t thread;
    if (pthread_create(&thread, NULL, worker, NULL)) return 2;
    pid_t child = fork();
    if (child < 0) return 2;
    if (!child) {
        /* CCPD inherits a SIGCHLD handler that requests daemon termination. */
        struct sigaction action = {0};
        action.sa_handler = child_exit;
        sigemptyset(&action.sa_mask);
        if (sigaction(SIGCHLD, &action, NULL)) _exit(2);
        /* Root matches CCPD. A nonexistent destination and job cannot cancel
         * any user job, but force CUPS to handle/localize an actual error. */
        cupsSetUser("root");
        int result = cupsCancelJob("LBP2900_nonexistent_cancel_regression", 2147483647);
        struct sigaction restored;
        if (sigaction(SIGCHLD, NULL, &restored) || restored.sa_handler != child_exit) _exit(5);
        _exit(termination_requested ? 4 : result ? 3 : 0);
    }
    int status;
    if (waitpid(child, &status, 0) != child) return 2;
    printf("child_signal=%d child_exit=%d\n", WIFSIGNALED(status) ? WTERMSIG(status) : 0,
           WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
