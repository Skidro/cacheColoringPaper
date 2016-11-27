# Stop lightdm service
service lightdm stop

# Setup page coloring
echo 0x0001F000 > /sys/kernel/debug/palloc/palloc_mask
mount -t cgroup xxx /sys/fs/cgroup
mkdir /sys/fs/cgroup/part1
mkdir /sys/fs/cgroup/part2
echo 0 > /sys/fs/cgroup/part1/cpuset.cpus
echo 1-11 > /sys/fs/cgroup/part2/cpuset.cpus
echo 0 > /sys/fs/cgroup/part1/cpuset.mems
echo 0 > /sys/fs/cgroup/part2/cpuset.mems
echo 0-15 > /sys/fs/cgroup/part1/palloc.bins
echo 16-31 > /sys/fs/cgroup/part2/palloc.bins

# Choose normal policy
echo 0 > /sys/kernel/debug/palloc/use_palloc
