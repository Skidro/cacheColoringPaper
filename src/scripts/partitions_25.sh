# Reset the current way partitioning
pqos -R

# Set the number of ways for cache partitions
pqos -e "llc:0=0x0001f;llc:1=0xfffe0;"

# Associate cores with partitions
pqos -a "llc:0=0;llc:1=1-11;"
