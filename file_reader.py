# You need to implement the "get" and "head" functions.
import os
class FileReader:
    def __init__(self):
        pass

    def get(self, filepath, cookies=""):
        """
        Returns a binary string of the file contents, or None.
        """
        # print(os.path.exists(filepath),filepath)
        if(os.path.exists(filepath)):
            if(os.path.isdir(filepath)):
                dir = f"<html><body><h1>{filepath}</h1></body></html>"
                return dir.encode("utf-8")
            else:
                f = open(filepath, "rb")
                file = f.read()
                f.close()
                return file
        else:
            return None

    def head(self, filepath, cookies=""):
        """
        Returns the size to be returned, or None.
        """

        if (os.path.exists(filepath)):
            if (os.path.isdir(filepath)):#size of dir, would be the html string
                return len(self.get(filepath))
            else:#otherwise its a file 
                return os.path.getsize(filepath)

        return None