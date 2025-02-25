import whisper
import ffmpeg
import shutil
import sys
import os

MODEL_SIZE: str = 'medium'
TMP_DIRECTORY: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')

def isMp4() -> bool:
    '''
    Checks if the input file is an MP4 file.
    Returns:
        bool: True if the input file has a '.mp4' extension, False otherwise.
    '''
    inputDir: str = sys.argv[1]
    fileExtension: str = inputDir[-4:]
    return fileExtension == '.mp4'

def isMp3() -> bool:
    '''
    Checks if the input file is an MP3 file.

    Returns:
        bool: True if the file extension is '.mp3', False otherwise.
    '''
    inputDir: str = sys.argv[1]
    fileExtension: str = inputDir[-4:]
    return fileExtension == '.mp3'

def isValidFileType() -> bool:
    '''
    Determines whether the input file type is valid (MP4 or MP3).

    Returns:
        bool: True if the input file is either an MP4 or MP3, False otherwise.
    '''
    return isMp4() or isMp3()

def validateArgs() -> None:
    '''
    Validates command line arguments.

    Exits the program if the number of arguments is not equal to 3 or if the file type is invalid.
    '''
    if len(sys.argv) != 3:
        print('Usage: python genTranscript.py -[file directory to transcribe ".mp4" or ".mp3"] -[output directory of transcript]')
        exit(-1)

    if not isValidFileType():
        print('The input file must be either a ".mp3" or ".mp4" file')
        exit(-1)

def mp4_to_mp3(inputDir, outputDir) -> None:
    '''
    Converts an MP4 file to an MP3 file using ffmpeg.

    Args:
        inputDir (str): The input MP4 file path.
        outputDir (str): The output MP3 file path.
    '''
    ffmpeg.input(inputDir).output(outputDir, vn=None, acodec='libmp3lame', **{'q:a': '2'}).run(overwrite_output=True)
    
def transcribeMp3(inputDir) -> str:
    '''
    Transcribes audio from an MP3 file using the Whisper model.

    Args:
        inputDir (str): The path to the MP3 file.

    Returns:
        str: The transcribed text.
    '''
    model = whisper.load_model(MODEL_SIZE)
    result: dict[str, str | list] = model.transcribe(inputDir)
    return result['text']

def clearTmp() -> None:
    '''
    Clears the temporary directory by removing it and creating a new one.
    '''
    if os.path.exists(TMP_DIRECTORY):
        shutil.rmtree(TMP_DIRECTORY)
    os.mkdir(TMP_DIRECTORY)

def copyToTmp(inputDir) -> None:
    '''
    Copies the input file into the temporary directory.

    Args:
        inputDir (str): The path to the input file.
    '''
    shutil.copy(inputDir, TMP_DIRECTORY)

def winToLinuxPath(winPath: str) -> str:
    '''
    Converts a Windows-style path to a Linux (WSL) path.

    Args:
        winPath (str): A Windows file path (e.g., "C:\\Users\\username\\Videos\\video.mp4" or "C:/Users/username/Videos/video.mp4").

    Returns:
        str: The corresponding Linux path (e.g., "/mnt/c/Users/username/Videos/video.mp4").
    '''
    winPath = winPath.replace("\\", "/")
    driveLetter: str = winPath[0].lower()
    restOfPath: str = winPath[3:]
    linuxPath: str = f'/mnt/{driveLetter}/{restOfPath}'
    return linuxPath

def main():
    validateArgs()

    inputDir: str = sys.argv[1]
    outputDir: str = sys.argv[2]

    inputDir = winToLinuxPath(inputDir)
    outputDir = winToLinuxPath(outputDir)

    inputFilename = os.path.basename(inputDir)

    if isMp4(): 
        print('Converting file to ".mp3"...')
        mp4_to_mp3(inputDir, os.path.join(TMP_DIRECTORY, inputFilename[:-1] + '3'))
    elif isMp3(): 
        copyToTmp(inputDir)

    print('Transcribing audio...')
    transcript: str = transcribeMp3(os.path.join(TMP_DIRECTORY, inputFilename[:-1] + '3'))
    print('Done!')

    with open(os.path.join(outputDir, f'{inputFilename[:-4]}_transcript.txt'), 'w', encoding='utf-8') as file:
        file.write(transcript)

    print(f'Saved transcript to {outputDir}')
    print('Transcript:\n')
    print(transcript)

    clearTmp()

if __name__ == '__main__':
    main()