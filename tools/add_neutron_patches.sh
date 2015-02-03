#!/bin/sh

echo "THIS IS THE SCRIPT THAT WILL ADD NEUTRON PATCHES"

DIRECTORY="$1/src/neutron"
LIST_SRC="$2/test-patches.txt"

echo "CHECKING DIRECTORY $DIRECTORY"

if [ ! -d "$DIRECTORY" ]; then
  echo "DIRECTORY DOESN'T EXIST" 
  exit 1
fi

cd $DIRECTORY
# Ensure we're on toxBranch not master or other branches
git checkout -b toxBranch
git checkout toxBranch

# Fetch and cherry-pick patches into neutron src
while read p; do
  git fetch https://review.openstack.org/openstack/neutron $p
  git cherry-pick FETCH_HEAD
done <$LIST_SRC

# Ensure we're upto date with master even after cherry-picks
git rebase master
