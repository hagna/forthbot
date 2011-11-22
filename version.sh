#!/bin/sh
# Print additional version information for non-release trees.

usage() {
	echo "Usage: $0 [srctree]" >&2
	exit 1
}

cd "${1:-.}" || usage
if ! [ -e ".git" ]
then
    printf 'dirty'
else
# Check for git and a git repo.
if head=`git rev-parse --verify HEAD 2>/dev/null`; then
	# Do we have an untagged version?
	if git name-rev --tags HEAD | grep -E '^HEAD[[:space:]]+(.*~[0-9]*|undefined)$' > /dev/null; then
	        git describe | awk '{printf("%s", $(NF))}'
    else
        git describe --tags --abbrev=0 | awk '{printf("%s", $(NF))}'
    fi

	# Are there uncommitted changes?
	git update-index --refresh --unmerged > /dev/null
	if git diff-index --name-only HEAD | grep -v "^scripts/package" \
	    | read dummy; then
		printf '%s' -dirty
	fi

	# All done with git
	exit
fi
fi
