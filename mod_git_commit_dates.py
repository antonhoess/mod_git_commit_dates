#!/usr/bin/env python

"""This program aims to modify all commit dates of a given local git repository according to a given rule.
The callback function modify_dates() needs to be adapted to your personal needs.
Build for use on Linux. Should be not too hard to adapt the creation of the command string to Windows."""

from typing import List, Callable
from argparse import ArgumentParser
import git
import datetime
import os
import uuid


__author__ = "Anton Höß"
__copyright__ = "Copyright 2021"
__credits__ = list()
__license__ = "BSD"
__version__ = "0.1"
__maintainer__ = "Anton Höß"
__email__ = "anton.hoess42@gmail.com"
__status__ = "Development"


class ModGitCommitDates:
    """The git commit dates modifier class."""

    def __init__(self, repo_path: str, branch: str = "master") -> None:
        """ Initializes the object.

        Parameters
        ----------
        repo_path : str
            The local git repository's path.
        branch : str, default "master"
            The git branch name.
        """

        self._repo_path = repo_path
        self._branch = branch

        # Retrieve all commits from the repository
        self._repo = git.Repo(self._repo_path)
        self._commits = list(self._repo.iter_commits(self._branch))

        # Get list of all commit dates and hashes
        self._dates = [datetime.datetime.utcfromtimestamp(commit.committed_date) for commit in reversed(self._commits)]
        self._hashes = [commit.hexsha for commit in reversed(self._commits)]

        self._dates_mod = None
    # end def

    def print_ori_timestamps(self) -> None:
        """ Print the commit-hash-id, the commit- and author-timestamp as well
        as the time difference between these two."""

        for i, commit in enumerate(reversed(self._commits)):
            committed_date = datetime.datetime.utcfromtimestamp(commit.committed_date)
            authored_date = datetime.datetime.utcfromtimestamp(commit.authored_date)
            print(f"{i + 1: 03}: {commit.hexsha}")
            print(f"{i + 1: 03}: commit = {self._get_date_str(committed_date)}")
            print(f"{i + 1: 03}: author = {self._get_date_str(authored_date)}")
            print(f"{i + 1: 03}:   => diff = {committed_date - authored_date}")
        # end for
    # end def

    def print_different_days(self) -> None:
        """ Print the set of different days."""

        dates = list(set([d.date() for d in self._dates]))

        for i, date in enumerate(dates):
            print(f"{i + 1: 03}: {self._get_date_str(datetime.datetime.combine(date, datetime.time.min))}")
        # end for
    # end def

    def print_mod_timestamps(self) -> bool:
        """ Print the modified timestamps (if there already are such).

        Returns
        -------
        timestamps_already_modifier : bool
            Indicates if the timestamps already have been modified.
        """

        if not self._dates_mod:
            return False
        else:
            for i, date in enumerate(self._dates_mod):
                print(f"{i + 1: 03}: {self._get_date_str(date)}")
            # end for

            return True
        # end if
    # end def

    def modify_dates(self, cb_modify_dates: Callable[[List[datetime.datetime]], List[datetime.datetime]],
                     sort: bool = True) -> None:
        """ Calls a date modifier callback function which will modify the commit dates which will later on
        be used to update the git commit history.

        Parameters
        ----------
        cb_modify_dates : Callable[[List[datetime.datetime]], List[datetime.datetime]]
            The commit-hash-id to modify.
        sort : bool, default True
            Sorts the modified timestamps by date (more exactly by time).
            This is because it might happen that after modifying dates, the timestamps in the commit history are not
            anymore in order, as the time at the same day is not in order anymore)
        """

        self._dates_mod = cb_modify_dates(self._dates[:])

        if sort:
            self._dates_mod.sort()
        # end if
    # end def

    @staticmethod
    def _get_date_str(date: datetime.datetime.date) -> str:
        """ Creates a string containing the given datetime in a certain format.

        Parameters
        ----------
        date : datetime.datetime
            The timestamp to format to a string.

        Returns
        -------
        date_str : str
            The formatted date string.
        """

        return f"{date} ({date.strftime('%A')})"
    # end def

    def _get_cmd_str_single_commit(self, hash_id: str, date: datetime.datetime) -> str:
        """ Create the command string that sets the commit- and author-date of a commit specified by its
        hash-id to the given datetime.
        Git is somewhat flexible with the date format, so there's no need to use exactly the format
        Git uses e.g. in 'git log' ("Fri Jan 2 21:38:53 2009 -0800").
        Produces a single filter command for the one single specified commit.

        Parameters
        ----------
        hash_id : str
            The commit-hash-id to modify.
        date : datetime.datetime
            The date time to set the defined commit to.

        Returns
        -------
        cmd : str
            The generated command string.
        """

        cmd = f"""
#!/bin/bash

cd {self._repo_path}
export FILTER_BRANCH_SQUELCH_WARNING=1
git filter-branch -f --env-filter '

if [ $GIT_COMMIT = {hash_id} ]
then
  export GIT_AUTHOR_DATE="{date.astimezone()}"
  export GIT_COMMITTER_DATE="{date.astimezone()}"
fi'
"""

        return cmd

    # end def

    def _get_cmd_str_all_commits(self) -> str:
        """ Create the command string that sets the commit- and author-date of a commit specified by its
        hash-id to the given datetime.
        Git is somewhat flexible with the date format, so there's no need to use exactly the format
        Git uses e.g. in 'git log' ("Fri Jan 2 21:38:53 2009 -0800").
        Produces a large single filter command for all commits.

        Returns
        -------
        cmd : str
            The generated command string.
        """

        cmd = f"""
#!/bin/bash

cd {self._repo_path}
export FILTER_BRANCH_SQUELCH_WARNING=1
git filter-branch -f --env-filter '
"""

        for i, (date, hash_id) in enumerate(zip(self._dates_mod, self._hashes)):
            if i != 0:
                cmd += "el"

            cmd += f"if [ $GIT_COMMIT = {hash_id} ] ; then\n"

            cmd += f'  export GIT_AUTHOR_DATE="{date.astimezone()}"\n'
            cmd += f'  export GIT_COMMITTER_DATE="{date.astimezone()}"\n'
        # end for
        cmd += "fi'"

        return cmd
    # end def

    def update(self, mode: int = 1) -> bool:
        """ Performs the update on the git repository's commit timestamps.

        Parameters
        ----------
        mode : int, default 1
            The update mode. There's 0 and 1, but 0 doesn't work so far.

        Returns
        -------
        mod : bool
            Indicates if the update has been performed or if the timestamps need to get modified first.
        """

        if self._dates_mod:
            if mode == 0:
                # This mode doesn't work, because after the first command executed, the rest will not
                # make changes anymore and give the warning: "WARNING: Ref 'refs/heads/master' is unchanged"
                for date, hash_id in zip(self._dates_mod, self._hashes):
                    cmd = self._get_cmd_str_single_commit(hash_id, date)
                    print(cmd)

                    os.system(cmd)
                # end for

            elif mode == 1:
                # This mode creates one single env-filter command, which works,
                # even if it doesn't seem to be the best solution
                cmd = self._get_cmd_str_all_commits()
                print(cmd)

                # We need to use a temp. bash file, since the commandline string
                # is too long to pass directly to os.system()
                fn = f"{str(uuid.uuid4())[:8]}.sh"
                text_file = open(fn, "w")
                text_file.write(cmd)
                text_file.close()

                # Execute command
                os.system(f"bash {fn}")

                # Remove temp. file
                os.remove(fn)
            # end if

            return True

        else:
            return False
        # end if
    # end def
# end class


def modify_dates(dates: List[datetime.datetime]):
    """ Modifies the commit timestamps - this example just moves it by one day into the future.

    Parameters
    ----------
    dates : list of datetime.datetime
        The timestamps to modify.

    Returns
    -------
    dates_mod : list of datetime.datetime
        The modified timestamps.
    """

    for i, date in enumerate(dates):
        dates[i] += datetime.timedelta(days=1)
    # end for

    return dates
# end def


def main():
    """ The main program."""

    # Read parameters
    parser = ArgumentParser()
    parser.add_argument("-p", "--path", default=".",
                        help="Specifies the repository path.")
    parser.add_argument("-y", "--yes", action='store_true', default=False,
                        help="Indicates if there was already a git repository backup created.")

    args = parser.parse_args()

    # Check for backup
    if not args.yes:
        print("!!! Create a backup of your repository before running this program on it!!!")
        backup = input("Did you create a backup? [Y/n]")

        if backup.strip().lower() != "y":
            print("Program quit. Create a backup of your git repository first!")
            exit(1)
        # end if
    # end if

    # Create the main object
    mod = ModGitCommitDates(args.path)

    # Modify the dates (the original ones will be preserved and a copy of them will be modified)
    mod.modify_dates(modify_dates)

    # Do some debug printing
    print("\n" + "=" * 50 + "\n")
    print("Both timestamps and time diff:")
    mod.print_ori_timestamps()
    print("\n" + "=" * 50 + "\n")
    print("Set with different days:")
    mod.print_different_days()
    print("\n" + "=" * 50 + "\n")
    print("Modified timestamps:")
    mod.print_mod_timestamps()
    print("\n" + "=" * 50 + "\n")

    # Perform the actual update task
    mod.update(mode=1)
# end def


if __name__ == "__main__":
    main()
# end def
