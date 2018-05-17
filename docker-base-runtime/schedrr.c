/* Set a real-time scheduling policy, then drop privileges and exec a program.
 * This is intended to be a setuid binary. To minimise the attack surface, it
 * does not take any command-line arguments, and is hard-coded to set the
 * policy to SCHED_RR with priority 1.
 */

#include <unistd.h>
#include <sys/types.h>
#include <stdio.h>
#include <sched.h>

int main(int argc, char * const *argv)
{
    int result;
    struct sched_param param = {};

    if (argc < 2)
    {
        fputs("Usage: schedrr program [args]\n", stderr);
        return 2;
    }
    param.sched_priority = 1;
    result = sched_setscheduler(0, SCHED_RR, &param);
    if (result != 0)
    {
        perror("sched_setscheduler failed");
        return 1;
    }
    /* Drop privileges */
    result = seteuid(getuid());
    if (result != 0)
    {
        perror("seteuid failed");
        return 1;
    }
    execvp(argv[1], argv + 1);
    /* If execvp returns, it definitely failed */
    perror("execvp failed");
    return 1;
}
