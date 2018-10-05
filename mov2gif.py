import argparse,subprocess,sys,os,json,glob,platform

def ffmpeg(movie,*args):
	cmd=['ffmpeg','-v','error','-i',movie]+[str(x) for x in args]
	subprocess.check_call(cmd)

def gifsicle(infile, outfile, *args):
	cmd=['gifsicle'] + list(args) + ['-o', outfile, infile]
	subprocess.check_call(cmd)

def rawConvertWithWidth(movie,output,width, fps, colors):
	filters="scale={0}:-1:flags=lanczos,eq=gamma={1}".format(width,gamma)
	palette_file = 'temp_palette.png'
	ffmpeg(movie,'-vf',filters+',palettegen=max_colors={}'.format(colors),'-y',palette_file)
	fps_filter =''
	if fps is not None:
		fps_filter=', fps={}'.format(fps)
	ffmpeg(movie,'-i',palette_file,'-lavfi',filters+' [x]; [x][1:v] paletteuse' + fps_filter ,'-y',output)
	os.unlink(palette_file)

def lossyOptimize(ingif, outgif):
	gifsicle(ingif, outgif, '-O3', '--lossy=80')

def convertWithWidth(movie, output, width, lossy, fps, colors):
	if lossy:
		try:
			temp_gif = 'temp.gif'
			rawConvertWithWidth(movie, temp_gif, width, fps, colors)
			lossyOptimize(temp_gif, output)
		finally:
			try:
				os.unlink(temp_gif)
			except OSError:
				pass

	else:
		rawConvertWithWidth(movie, output, width, fps, colors)

	return os.path.getsize(output)//1024


def getGIFName(name):
	return os.path.splitext(name)[0]+'.gif'

def convertDividedRateToFPS(rate):
	dividend, divisor = rate.split('/')
	return int(round(float(dividend) / float(divisor)))

def getMovieInfo(movie):
	data=subprocess.check_output([
		'ffprobe','-print_format','json','-i',movie,'-show_entries','streams','-select_streams','v','-loglevel','-8']
	)
	jdata = json.loads(data)
	# TODO: is the video stream always the first one?
	stream = jdata['streams'][0]
	return {
		'width': stream['width'],
		'fps': convertDividedRateToFPS(stream['r_frame_rate'])
	}

def replaceWithGlobs(args):
	out=[]
	for arg in args:
		if '?' in arg or '*' in arg or '+' in arg:
			out.extend(glob.glob(arg))
		else:
			out.append(arg)
	return out

WIDTHS=(1280,1024,960,800,720,640,600,550,500,450,400,350,320,300,250,200,150,100,75,50)

SITES={
	'twitter': 15*1024, # twitter knows what a megabyte is!
	'mobile-twitter': 5*1024, # WHY IS MOBILE DIFFERENT?
	'tumblr':3000, # TODO: test if this is really 3*1024 instead
	'reddit':99999, # I have no idea what the limit actaully is.
	'sms': 2000 # this is specifically MightyText, other SMS platforms naturally have other limits
}
# todo: be smarter about inserting original width?
gamma = 1.1
# TODO: let gamma be controllable!

parser = argparse.ArgumentParser(description='Convert movies to GIFs')
parser.add_argument('movies', metavar='FILE', type=str, nargs='+',
                    help='files to convert')

parser.add_argument('--target', dest='target', action='store',
                    default='twitter',
                    help='File size in kilobytes to target (or a site name)')

parser.add_argument('-c','--colors', dest='colors', action='store',
                    default=256,type=int,
                    help='Max colors to use in GIF (256 is max!)')

parser.add_argument('-o','--original', dest='original', action='store_true',
                    help='Try at original size too, with no resizing')

parser.add_argument('-l','--lossy', dest='lossy', action='store_true',
                    help='Do a lossy convert on GIFs')

parser.add_argument('--max', dest='maxwidth', action='store',type=int,
                    help='max width to bother trying')


parser.add_argument('-w','--overwrite', dest='overwrite', action='store_true',
                    help='Overwrite existing GIFs')

parser.add_argument('--fps', dest='fps', action='store',type=int,
                    help='change FPS')

args = parser.parse_args()
if platform.system() == 'Windows':
	args.movies = replaceWithGlobs(args.movies)

target_size = SITES.get(args.target)
if target_size is None:
	target_size = int(args.target)

for infile in args.movies:
	found=False
	print 'processing',infile
	output_file = getGIFName(infile)
	if os.path.exists(output_file) and not args.overwrite:
		print 'GIF already exists, skipping'
		continue
	info = getMovieInfo(infile)
	orig_width = info['width']

	print 'original width: {} fps: {}'.format(orig_width, info['fps'])
	if info['fps']>30 and args.fps is None:
		args.fps = 30
		print 'Auto-adjusting FPS to 30'
	if args.original and orig_width not in WIDTHS:
		widths=[orig_width]+list(WIDTHS)
	else:
		widths=WIDTHS
	max_width = orig_width
	if args.maxwidth:
		max_width = min(orig_width, args.maxwidth)

	for width in widths:
		if width>max_width:
			continue


		size = convertWithWidth(infile, output_file, width, args.lossy, args.fps, args.colors)

		if size<target_size:
			print 'Got it at {}kb with width of {}'.format(size,width)
			found=True
			break
		else:
			print 'width of {} resulted in {}kb GIF. Too big!'.format(width, size)
	if not found:
		print 'Failed to find a small enough video!'
		if os.path.exists(output_file):
			os.unlink(output_file)

