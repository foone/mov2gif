import argparse,subprocess,sys,os,json,glob,platform

def ffmpeg(movie,*args):
	cmd=['ffmpeg','-v','warning','-i',movie]+[str(x) for x in args]
	subprocess.check_call(cmd)

#filters="fps=$3,scale=$4:-1:flags=lanczos"
def convertWithWidth(movie,output,width,colors=256):
	filters="scale={0}:-1:flags=lanczos,eq=gamma={1}".format(width,gamma)
	palette_file = 'temp_palette.png'
	ffmpeg(movie,'-vf',filters+',palettegen=max_colors={}'.format(colors),'-y',palette_file)
	ffmpeg(movie,'-i',palette_file,'-lavfi',filters+' [x]; [x][1:v] paletteuse=dither=none, fps=12','-y',output)
	os.unlink(palette_file)
	return os.path.getsize(output)//1024

def getGIFName(name):
	return os.path.splitext(name)[0]+'.gif'

def getOriginalWidth(movie):
	data=subprocess.check_output([
		'ffprobe','-print_format','json','-i',movie,'-show_entries','streams','-select_streams','v','-loglevel','-8']
	)
	return json.loads(data)['streams'][0]['width']

def replaceWithGlobs(args):
	out=[]
	for arg in args:
		if '?' in arg or '*' in arg or '+' in arg:
			out.extend(glob.glob(arg))
		else:
			out.append(arg)
	return out

WIDTHS=(1280,1024,960,800,720,640,600,500,400,300,250,200,150,100,75,50)

target_size = 15000
SITES={
	'twitter': 15000,
	'tumblr':3000,
	'sms':2000,
}

gamma = 1.1

parser = argparse.ArgumentParser(description='Convert movies to GIFs')
parser.add_argument('movies', metavar='FILE', type=str, nargs='+',
                    help='files to convert')
parser.add_argument('--target', dest='target', action='store',
                    default='twitter',
                    help='File size in kilobytes to target (or a site name)')

parser.add_argument('-c','--colors', dest='colors', action='store',
                    default=256,type=int,
                    help='Max colors to use in GIF (256 is max!)')

args = parser.parse_args()
if platform.system() == 'Windows':
	args.movies = replaceWithGlobs(args.movies)
target_size = SITES.get(args.target)
if target_size is None:
	target_size = int(args.target)

for infile in args.movies:
	found=False
	print 'processing',infile
	output_file=getGIFName(infile)
	orig_width = getOriginalWidth(infile)
	print 'original width:',orig_width
	for width in WIDTHS:
		if width>orig_width:
			continue
		size=convertWithWidth(infile,output_file,width, args.colors)
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

