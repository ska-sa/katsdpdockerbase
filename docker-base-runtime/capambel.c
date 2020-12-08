/* Copyright (c) 2020, National Research Foundation (SARAO)
 *
 * Licensed under the BSD 3-Clause License (the "License"); you may not use
 * this file except in compliance with the License. You may obtain a copy
 * of the License at
 *
 *   https://opensource.org/licenses/BSD-3-Clause
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* Transfers permitted capabilities to the ambient set, then executes
 * another program. To use
 *
 * 1. Compile by running 'make'.
 * 2. Make the program executable by only the user/group you want to use it.
 * 3. Grant the program the capabilities that it should pass on e.g.
 *    setcap cap_net_raw+p capambel.
 *
 * By default it applies all permitted capabilities, but the -c option can
 * be used to give a capability specification, as parsed by cap_to_text(3),
 * from which permitted capabilities will be taken.
 */

#ifndef _GNU_SOURCE
# define _GNU_SOURCE
#endif
#include <stdio.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <unistd.h>
#include <getopt.h>
#include <sys/capability.h>
#include <sys/prctl.h>

static void check(int result, const char *name)
{
    if (result != 0)
    {
        perror(name);
        exit(1);
    }
}

static void check_ptr(void *ptr, const char *name)
{
    if (ptr == NULL)
    {
        perror(name);
        exit(1);
    }
}

static void usage(void)
{
    fputs("Usage: capambel [-v] [-c cap,...,cap+p] -- <program> [<args>...]\n", stderr);
    exit(2);
}

int main(int argc, char * const argv[])
{
    static const struct option options[] =
    {
        {"verbose", no_argument, 0, 'v'},
        {"capabilities", required_argument, 0, 'c'},
        {0, 0, 0, 0}
    };

    cap_t cap;
    cap_t req_cap = NULL;
    cap_value_t value;
    int opt;
    bool verbose = false;

    do
    {
        switch (opt = getopt_long(argc, argv, "vc:", options, NULL))
        {
        case -1:
            break;
        case 'v':
            verbose = true;
            break;
        case 'c':
            req_cap = cap_from_text(optarg);
            check_ptr(req_cap, "cap_from_text");
            break;
        default:
            usage();
        }
    } while (opt != -1);
    if (optind >= argc)
        usage();

    cap = cap_get_proc();
    check_ptr(cap, "cap_get_proc");

    for (value = 0; value <= CAP_LAST_CAP; value++)
    {
        cap_flag_value_t state;
        check(cap_get_flag(req_cap ? req_cap : cap, value, CAP_PERMITTED, &state), "cap_get_flag");
        if (state)
        {
            /* Ambient flag can only be raised if the flag is permitted and inheritable. */
            check(cap_set_flag(cap, CAP_PERMITTED, 1, &value, CAP_SET), "cap_set_flag");
            check(cap_set_flag(cap, CAP_INHERITABLE, 1, &value, CAP_SET), "cap_set_flag");
        }
    }
    check(cap_set_proc(cap), "cap_set_proc");
    if (verbose)
    {
        char *text;
        text = cap_to_text(cap, NULL);
        check_ptr(text, "cap_to_text");
        fprintf(stderr, "Set process capabilities to %s\n", text);
        cap_free(text);
    }

    for (value = 0; value <= CAP_LAST_CAP; value++)
    {
        cap_flag_value_t state;
        check(cap_get_flag(req_cap ? req_cap : cap, value, CAP_PERMITTED, &state), "cap_get_flag");
        if (state)
        {
            /* Older versions of libcap don't support cap_set_ambient, so use
             * prctl directly.
             */
            check(prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, value, 0, 0), "prctl");
            if (verbose)
            {
                char *name;
                name = cap_to_name(value);
                check_ptr(name, "cap_to_name");
                fprintf(stderr, "Added %s to ambient set\n", name);
                cap_free(name);
            }
        }
    }
    cap_free(cap);
    if (req_cap)
        cap_free(req_cap);

    execvp(argv[optind], argv + optind);
    perror("execvp");
    return 1;
}
