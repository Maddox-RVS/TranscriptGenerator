import tempfile
import whisper
import ffmpeg
import shutil
import torch
import sys
import os

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MODEL_SIZES: list[str] = ['tiny.en', 
                        'tiny', 
                        'base.en', 
                        'base', 
                        'small.en', 
                        'small', 
                        'medium.en', 
                        'medium', 
                        'large-v1', 
                        'large-v2', 
                        'large-v3', 
                        'large', 
                        'large-v3-turbo', 
                        'turbo']
TMP_DIRECTORY: str = tempfile.mkdtemp()

def isMp4(inputDir: str) -> bool:
    '''
    Checks if the input file is an MP4 file.
    Returns:
        bool: True if the input file has a '.mp4' extension, False otherwise.
    '''
    fileExtension: str = inputDir[-4:]
    return fileExtension == '.mp4'

def isMp3(inputDir: str) -> bool:
    '''
    Checks if the input file is an MP3 file.

    Returns:
        bool: True if the file extension is '.mp3', False otherwise.
    '''
    fileExtension: str = inputDir[-4:]
    return fileExtension == '.mp3'

def isValidFileType(inputDir: str) -> bool:
    '''
    Determines whether the input file type is valid (MP4 or MP3).

    Returns:
        bool: True if the input file is either an MP4 or MP3, False otherwise.
    '''
    return isMp4(inputDir) or isMp3(inputDir)

def __validateArgs__(vargs: list[str]) -> None:
    '''
    Validates command line arguments.

    Exits the program if the number of arguments is not equal to 3 or if the file type is invalid.
    '''
    if len(vargs) != 4:
        print('Usage: python genTranscript.py -[file directory to transcribe ".mp4" or ".mp3"] -[output directory of transcript] -[model size]')
        exit(-1)

    if not isValidFileType(vargs[1]):
        print('The input file must be either a ".mp3" or ".mp4" file')
        exit(-1)

    if (vargs[3] not in MODEL_SIZES):
        print(f'Model size must be one of the following:')
        for modelSize in MODEL_SIZES: print(modelSize)
        exit(-1)

def mp4_to_mp3(inputDir: str, outputDir: str) -> None:
    '''
    Converts an MP4 file to an MP3 file using ffmpeg.

    Args:
        inputDir (str): The input MP4 file path.
        outputDir (str): The output MP3 file path.
    '''
    ffmpeg.input(inputDir).output(outputDir, vn=None, acodec='libmp3lame', **{'q:a': '2'}).run(overwrite_output=True)
    
def __transcribeMp3__(inputDir: str, modelSize: str) -> str:
    '''
    Transcribes audio from an MP3 file using the Whisper model.

    Args:
        inputDir (str): The path to the MP3 file.

    Returns:
        str: The transcribed text.
    '''
    model = whisper.load_model(modelSize, device=DEVICE)
    result: dict[str, str | list] = model.transcribe(inputDir)
    return result['text']

def __copyToTmp__(inputDir) -> None:
    '''
    Copies the input file into the temporary directory.

    Args:
        inputDir (str): The path to the input file.
    '''
    shutil.copy(inputDir, TMP_DIRECTORY)

def transcribe(inputDir: str, outputDir: str, modelSize: str):
    '''
    Transcribes the audio from an input media file and saves the transcript.

    Transcribes the audio using the specified Whisper model size and writes
    the transcript to a text file in the output directory.

    Args:
        inputDir (str): The path to the input media file (either '.mp4' or '.mp3').
        outputDir (str): The directory where the transcript file will be saved.
        modelSize (str): The Whisper model size to use for transcription. Must be one of
                         the allowed sizes listed in MODEL_SIZES.
    '''
    __validateArgs__([__name__, inputDir, outputDir, modelSize])

    inputFilename = os.path.basename(inputDir)

    if isMp4(inputDir): 
        print(f'Converting {inputDir} to ".mp3"...')
        mp4_to_mp3(inputDir, os.path.join(TMP_DIRECTORY, inputFilename[:-1] + '3'))
    elif isMp3(inputDir): 
        __copyToTmp__(inputDir)

    print(f'Found {DEVICE} device')
    print(f'Transcribing audio using {DEVICE}...')
    transcript: str = __transcribeMp3__(os.path.join(TMP_DIRECTORY, inputFilename[:-1] + '3'), modelSize)
    print('Done!')

    with open(os.path.join(outputDir, f'{inputFilename[:-4]}_transcript.txt'), 'w', encoding='utf-8') as file:
        file.write(transcript)

    print(f'Saved transcript to {outputDir}')
    print('Transcript:\n')
    print(transcript)

def main():
    __validateArgs__(sys.argv)
    inputDir: str = sys.argv[1]
    outputDir: str = sys.argv[2]
    modelSize: str = sys.argv[3]
    transcribe(inputDir, outputDir, modelSize)
    shutil.rmtree(TMP_DIRECTORY)

if __name__ == '__main__':
    main()