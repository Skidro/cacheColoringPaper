class Helper(object):
        """ This class defines helper functions to be used by other classes """
        def bit_mask(self, number):
                """ A generator function which returns the set bits in a number
                    in their original positions iteratively. This is a very
                    efficient implementation """
                while(number):
                        # This line extracts the first set bit in the number
                        set_bit = number & (~number + 1)

                        # Return the set bit to the user
                        yield set_bit

                        # Reset the bit for the next iteration
                        number ^= set_bit

                return

        def bit_numbers(self, number):
                """ A function which returns the digit value of set bit positions
                    in a number """
                bit_list = []

                # Iterate over the set bits in the number
                index = 0
                for bits in self.bit_mask(number):
                        bits >>= index
                        while (bits):
                                bits >>= 1
                                index += 1
                        bit_list.append(index-1)

                return bit_list