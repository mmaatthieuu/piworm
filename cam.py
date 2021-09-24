#!/usr/bin/python3
import pathlib

import numpy as np
import time
import picamera
import argparse
import os.path

import NPImage as npi



import cam_lib as cl


parser = argparse.ArgumentParser()

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-vv", "--vverbose", help="increase more output verbosity",
                    action="store_true")
parser.add_argument("-p", "--preview", help="display camera preview",
                    action='store_true')
parser.add_argument("-t", "--timeout", help="time (in s) before takes picture and shuts down",
                    default=10, nargs='?', type=int)
parser.add_argument("-ti", "--time-interval", help="time interval between frames in seconds",
                    default=5, nargs='?', type=int)
parser.add_argument("-avg", "--average", help="number of pictures to average at each frame",
                    default=3, nargs='?', type=int)
parser.add_argument("-o","--output", help="output filename",
                    nargs=1, type=str)
parser.add_argument("-q", "--quality", help="set jpeg quality <0 to 100>",
                    nargs='?', type=int, default=75)
parser.add_argument("-iso", "--iso", help="sets the apparent ISO setting of the camera",
                    nargs='?', type=int, default=100)
parser.add_argument("-ss", "--shutter-speed", help="sets the shutter speed of the camera in microseconds",
                    type=int, default=0)
parser.add_argument("-x", "--compress", help="",
                    nargs='?', type=int, const=1000)
parser.add_argument("-sf", "--start-frame", help="input the frame number to start to (default = 0)",
                    type=int, default=0)
parser.add_argument("-r", type=float)
parser.add_argument("-th", type=int)

args = parser.parse_args()


local_tmp_dir = ".campy_local_save/"
if args.output is not None:
    absolute_output_folder = pathlib.Path(cl.get_folder_name(args.output[0])).absolute()
    output_filename = cl.get_file_name(args.output[0])

# print(absolute_output_folder)
# print(output_filename)




def init():

    if args.vverbose:
        args.verbose = True

    if args.verbose:
        cl.print_args(args)

    if args.compress is not None:
        try:
            os.mkdir(local_tmp_dir)
            print("Folder ", local_tmp_dir, " created")
        except FileExistsError:
            pass
            # os.remove(".campy_local_save/*")
        os.chdir(local_tmp_dir)





def main():
    init()

    nPicsPerFrames = args.average
    n_frames_total = args.timeout // args.time_interval

    try:
        delay = 0
        with picamera.PiCamera(resolution='3296x2464') as camera:
            camera.iso = args.iso
            #camera.CAPTURE_TIMEOUT = 10

            if args.preview:
                camera.start_preview()

            if args.verbose:
                print("Starting camera...")
            time.sleep(2)  # let the camera warm up and set gain/white balance

            if args.shutter_speed is not None:
                g = camera.awb_gains
                camera.awb_mode = "off"
                camera.awb_gains = g

                camera.shutter_speed = args.shutter_speed
                camera.exposure_mode = 'off'

            if args.verbose:
                print("Camera successfully started")
                print("Current a/d gains: {}, {}".format(camera.analog_gain, camera.digital_gain))

            for k in range(args.start_frame, n_frames_total):
                start_time = time.time()
                pictures_to_average = np.empty((2464, 3296), dtype=np.uint8)

                if args.vverbose:
                    print("Starting capture of frame %d / %d" % (k+1, n_frames_total))
                elif args.verbose:
                    print("\rStarting capture of frame %d / %d" % (k + 1, n_frames_total), end="")

                for i in range(nPicsPerFrames):
                    output = npi.NPImage()
                    try:

                        camera.capture(output, 'yuv', use_video_port=False)

                        #pictures_to_average = pictures_to_average + \
                                              cl.compressor(output.get_data(),args.r,args.th) // args.average
                        pictures_to_average = pictures_to_average + output.get_data()// args.average
                        #print(np.max(pictures_to_average))
                    except picamera.exc.PiCameraRuntimeError as error:
                        print("Error 1 on frame %d" % k)
                        print(error)
                    except RuntimeError:
                        print("Error 2 on frame %d" % k)

                if args.output is not None:
                    cl.save_image(pictures_to_average, k, absolute_output_folder,
                                  output_filename, args.compress, n_frames_total, args.quality)


                execTime = (time.time() - start_time)
                if args.vverbose:
                    print("Finished capture of frame %d in %fs" % (k + 1, execTime))

                diff_time = args.time_interval - execTime
                if diff_time - delay > 0:
                    sleep_time = args.time_interval - execTime - delay
                    if args.vverbose:
                        print("Waiting for %fs" % sleep_time)
                    time.sleep(sleep_time)
                    delay = 0
                else:
                    delay -= diff_time
                    if args.verbose:
                        print('\nFrame %fs late' % -diff_time)
                        print('Delay : %fs' % delay)
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    # else:
    #     print("\nOops... Something went wrong.\n")
    finally:
        if args.verbose:
            print("Closing camera...")
        camera.close()

        if args.verbose:
            print("Over.")

if __name__ == "__main__":
    main()
