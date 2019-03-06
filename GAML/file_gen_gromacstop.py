from GAML.functions import file_gen_new, file_size_check, function_file_input
from GAML.function_prolist import Pro_list


class File_gen_gromacstop(object):
    """
    This class is used to generate GROMACS topology file based on given charge_path file,
    to be more precise, the symmetry_list also can be input as a reference. Generally,
    the charge_path either can be a path linking a real file, or can be list.

    However, if symmetry_list does not exist, the sequence of charge pairs is determined
    by the [systems] directive in the GROMACS topology file.
    """

    def __init__(self,*args,**kwargs):
        self.log = {'nice':True,}

        if 'reschoose' in kwargs and kwargs['reschoose'] is not None:
            self.reschoose = kwargs['reschoose']
        else:
            self.reschoose = 'All'

        if 'toppath' in kwargs and kwargs['toppath'] is not None:
            self.toppath = kwargs['toppath']
            log = file_size_check(self.toppath,fsize=50)
            if not log['nice']:
                self.log['nice'] = False
                self.log['info'] = log['info']
                return
            fp = self._f_pro_topfile(self.toppath)
            if not self.log['nice']: return
        else:
            self.log['nice'] = False
            self.log['info'] = 'Error: the parameter toppath is missing'
            return        

        if 'in_keyword' in kwargs and kwargs['in_keyword'] is not None:
            self.in_keyword = kwargs['in_keyword']
        else:
            self.in_keyword = 'PAIR'
            
        if 'cut_keyword' in kwargs and kwargs['cut_keyword'] is not None:
            self.cut_keyword = kwargs['cut_keyword']
        else:
            self.cut_keyword = 'MAE'
            
        if 'charge_path' in kwargs and kwargs['charge_path'] is not None:
            # function_file_input
            charge_path = kwargs['charge_path']
            if isinstance(charge_path,str):           
                log = file_size_check(charge_path,fsize=50)
                if not log['nice']:
                    self.log['nice'] = False
                    self.log['info'] = log['info']
                    return
                self.file_line_chargepath = charge_path

                log, self.prochargefile = function_file_input(charge_path,comment_char='#',dtype=float,
                                                              bool_tail=False,in_keyword=self.in_keyword,
                                                              cut_keyword=self.cut_keyword)
                if not log['nice']:
                    self.log['nice'] = False
                    self.log['info'] = log['info']
                    return
                
            elif isinstance(charge_path,list):           
                dump_value = self._f_list_dcheck(charge_path)
                if not self.log['nice']: return
                self.prochargefile = charge_path
                self.file_line_chargepath = 'Note: charge_path input is a list'

            else:
                self.log['nice'] = False
                self.log['info'] = 'Error: wrong defined charge_path parameter\n' + \
                                   'Error: it only can either be a list or a real file path'
                return
        else:
            self.log['nice'] = False
            self.log['info'] = 'Error: the parameter charge_path is missing'
            return


        if 'gennm' in kwargs and kwargs['gennm'] is not None:
            try:
                self.gennm = int(kwargs['gennm'])
                
                if self.gennm == 0 or self.gennm > len(self.prochargefile):
                    self.gennm = len(self.prochargefile)
                elif self.gennm < 0:
                    raise ValueError                                
            except ValueError:
                self.log['nice'] = False
                self.log['info'] = 'Error: the gennm has to be a positive integer\n' + \
                                   'Error gennm: '+ str(kwargs['gennm'])
                return                 
        else:
            self.gennm = len(self.prochargefile)

        if 'symmetry_list' in kwargs:
            symmetry_list = kwargs['symmetry_list']
        else:
            symmetry_list = None

        ndx = len(self.atomndx)           
        if symmetry_list is None:
            symmetry_list = list(range(ndx))
            symmetry_length = ndx
            self.file_line_symmetry = None
            
        elif isinstance(symmetry_list,list):
            if len(symmetry_list) == 0:
                symmetry_list = list(range(ndx))
                symmetry_length = ndx
                self.file_line_symmetry = None
            else:
                _par = Pro_list(symmetry_list=symmetry_list)
                if not _par.log['nice']:
                    self.log['nice'] = False
                    self.log['info'] = _par.log['info']
                    return
                symmetry_list = _par.symmetry_list
                symmetry_length = _par.symmetry_length
                self.file_line_symmetry = _par.file_line_symmetry
        else:
            self.log['nice'] = False
            self.log['info'] = 'Error: the parameter symmetry_list has to be a list'
            return


        if symmetry_length > ndx:
            self.log['nice'] = False
            self.log['info'] = 'Error: the symmetry_list and topfile are not corresponded'
            return

        count = 1
        lth = len(symmetry_list)
        ls = []
        for i in self.prochargefile[:self.gennm]:
            if len(i) < lth:
                print('Error: the chargefile and topfile are not corresponded')
                exit()
            elif len(i) > lth:
                ls.append(count)
            count += 1
            
        if len(ls) > 0:
            print('Warning: the number of charges are bigger than the atom numbers in the topfile')
            print('       : truncation will happen, only the number of leading charges will be used')
            print('       : the number of this charge pair is:')
            for count in ls:
                print(count,end='   ')
            print()

        self.refatomtype = []
        for i in symmetry_list:
            if isinstance(i,int):
                line = self.protopfile[self.atomndx[i]]
                self.refatomtype.append(line.split()[1])
            else:
                line_1 = self.protopfile[self.atomndx[i[0]]]
                atype = line_1.split()[1]
                if len(i) > 1:
                    for j in i[1:]:
                        line = self.protopfile[self.atomndx[j]]
                        if atype != line.split()[1]:
                            self.log['nice'] = False
                            self.log['info'] = 'Error: the atom_types under [atoms] directive in top file is not equivalent\n' + \
                                               'Error: symmetry_list:' + line_1[:-1] + '\n' + \
                                               line[:-1]
                            return
                self.refatomtype.append(atype)
                           
        dump_value = self._generator()
        if not self.log['nice']: return


        if 'fname' in kwargs and kwargs['fname'] is not None:
            self.fname = kwargs['fname']
        else:
            self.fname = 'GenGromacsTopfile'

                

    def _f_list_dcheck(self,list_input):
        """check if the input list dimensions and data-type, only 2D list is valid"""

        self.log['nice'] = True
        self.log['info'] = 'Error: the input_list is not properly defined'
        for i in list_input:
            if isinstance(i,list) and len(i) != 0:
                for j in i:
                    if not isinstance(j,(float,int)):
                        self.log['nice'] = False
                        return 0
            else:
                self.log['nice'] = False
                return 0
        return 1

    def procomments(self,string):
            if string.find(';') == -1:
                return string
            return string[:string.find(';')]


    def _f_pro_topfile(self,toppath):
        """process the topfile, and remove its all comments to a more tight format,
           the final parameters are, self.protopfile, self.atomtypendx, self.atomndx"""

        # self.protopfile
        with open(toppath,mode='rt') as f:
            self.protopfile = f.readlines()
                        
        i = 0
        atomtypendx = []
        atomndx = []
        syslist = []
        while i < len(self.protopfile):
            line = self.protopfile[i]

            # remove the comments
            line = self.procomments(line)

            if line.find('[') != -1:
                strtmp = ''
                for char in line:
                    if char != ' ' and char != '\t' and char != '\n':
                        strtmp += char
                line = strtmp

            if line == '[atomtypes]':
                j = i + 1
                while True:
                    if self.protopfile[j].find('[') != -1 or j >= len(self.protopfile):
                        break
                    subline = self.protopfile[j]
                    subltmp = self.procomments(subline).split()
                    
                    if len(subltmp) == 0 or (len(subltmp) > 0 and subltmp[0][0] == '#'):
                        j += 1
                        continue
                    if len(subltmp) == 6 or len(subltmp) == 7:
                        atomtypendx.append(j)
                    else:
                        self.log['nice'] = False
                        self.log['info'] = 'Error: wrong top file input\n' + \
                                           'Error: wrong entry,\n' + \
                                           subline
                        return 0
                    
                    j += 1
                i = j 

            elif line == '[atoms]':
                ls = []
                j = i + 1
                while True:
                    if self.protopfile[j].find('[') != -1 or j >= len(self.protopfile):
                        break
                    subline = self.protopfile[j]
                    subltmp = self.procomments(subline).split()
                    
                    if len(subltmp) == 0 or (len(subltmp) > 0 and subltmp[0][0] == '#'):
                        j += 1
                        continue
                    if len(subltmp) < 6 and len(subltmp) > 8:
                        self.log['nice'] = False
                        self.log['info'] = 'Error: wrong top file input\n' + \
                                           'Error: wrong entry,\n' + \
                                           subline
                        return 0
                    else:
                        ls.append(j)
                    
                    j += 1

                if len(ls) > 0:
                    atomndx.append(ls)
                i = j
                
            elif line == '[molecules]':
                j = i + 1
                while True:
                    if j >= len(self.protopfile) or self.protopfile[j].find('[') != -1:
                        break
                    subline = self.protopfile[j]
                    subltmp = self.procomments(subline).split()
                    
                    if len(subltmp) == 0 or (len(subltmp) > 0 and subltmp[0][0] == '#'):
                        j += 1
                        continue
                    if len(subltmp) == 2:
                        syslist.append( subltmp[0] )
                    else:
                        self.log['nice'] = False
                        self.log['info'] = 'Error: wrong top file input\n' + \
                                           'Error: wrong entry,\n' + \
                                           subline
                        return 0                        
                    j += 1
                i = j    
            
            else:
                i += 1

        
        # adjust the directives' sequence
        proatomndx = []      
        for res in syslist:
            bool_ndx = True
            print('For top file, processing residue < {:s} > ... '.format(res))
            for cmp in atomndx:
                line = self.protopfile[cmp[0]]
                if res == line.split()[3]:
                    bool_ndx = False
                    proatomndx.append(cmp)
                    break
            if bool_ndx:
                self.log['nice'] = False
                self.log['info'] = 'Error: for residue' + res + 'the corresponded [atoms] directive is not found'
                return 0 
                

        # select the residue based on given parameter, self.reschoose
        # self.atomtypendx, self.atomndx
        self.atomtypendx = atomtypendx
        if self.reschoose.upper() != 'ALL':
            
            count = 0
            self.atomndx = []
            for choose in syslist:
                if choose.upper() == self.reschoose.upper():
                    print('\nFor top file, choosing residue < {:s} >\n'.format(self.reschoose))
                    self.atomndx = proatomndx[count]
                    break
                count += 1

            if len(self.atomndx) == 0:
                self.log['nice'] = False
                self.log['info'] = 'Error: wrong reschoose parameter\n' + \
                                   'Error: no residue was chosen\n' + \
                                   'Error: the available residues are;' + syslist
                return 0
        else:
            print('\nFor top file, choosing all residue\n')
            self.atomndx = [i for j in proatomndx for i in j]

        return 1



    def _generator(self):
        """combine the charge file and top file, the defined_class parameter, self.outfile"""

        totatomtype = []
        for i in self.atomtypendx:
            ltmp = self.protopfile[i].split()
            totatomtype.append(ltmp[0])

        atomlist = []
        for i in self.atomndx:
            ltmp = self.protopfile[i].split()
            atomlist.append(ltmp[1])

        self.outfile = []
        for charge in self.prochargefile[:self.gennm]:

            # ATTENTION! Here is very important !!!
            # make a copy of self.protopfile, avoide the same memory address

            topfile = self.protopfile[:]


            count = 0
            for pair in charge:
                atype = self.refatomtype[count]
                try:
                    ndx = totatomtype.index(atype)
                except:
                    self.log['nice'] = False
                    self.log['info'] = 'Error: the atom_type in [atoms] is not defined in [atomtypes]\n' + \
                                       'Error:' + str(i)
                    return 0
                nm = self.atomtypendx[ndx]
                line = topfile[nm]
                ltmp = self.procomments(line).split()
                subline = ''
                if len(ltmp) == 6:
                    ltmp[2] = pair
                else:
                    ltmp[3] = pair
                for ch in ltmp:
                    subline += '{:>8}  '.format(ch)
                topfile[nm] = subline + '\n'

                # process the [atoms] directive
                scount = 0
                for i in atomlist:
                    if i == atype:
                        snm = self.atomndx[scount]
                        
                        line = topfile[snm]
                        ltmp = self.procomments(line).split()
                        subline = ''
                        if len(ltmp) == 6:
                            ltmp.append(pair)
                        else:
                            ltmp[6] = pair
                        for ch in ltmp:
                            subline += '{:>8}  '.format(ch)
                        topfile[snm] = subline + '\n'
                    scount += 1
                    
                count += 1
                            
            self.outfile.append(topfile)

        return 1
    

    # generate files
    
    def file_print(self):
        
        if len(self.outfile) == 0:
            print('Warning: no file is going to output')
            print('       : please try to change the input chargefile')
            exit()
        else:
            print('\nOne sample of generated GROMACS_top files is:\n')

            print('  [ atoms ]')
            for i in self.atomndx:
                print(self.outfile[0][i],end='')
            
            print('\nDo you want to continue?  y/yes, else quit')
            print('    this will generate \'top\' files >',end='    ')
            get_input = input()
            if get_input.upper() != 'Y' and get_input.upper != 'YES':
                print('\nWarning: you have decided to quit ...')
                print('       : nothing is generated\n')
                exit()
            else:
                print('\nGreat! Going to generate files ...\n')
                
        
        topnamelist = []
        for top in self.outfile:
            
            fname = file_gen_new(self.fname,fextend='top',foriginal=False)

            topnamelist.append(fname)
            
            with open(fname,mode='wt') as f:
                for line in top:
                    f.write(line)

        fnamelist = self.fname + '_NameList'
        fnamelist = file_gen_new(fnamelist,fextend='txt',foriginal=False)
        
        with open(fnamelist,mode='wt') as f:
            f.write('# This is a collection of all the generated GROMACS topfile names \n')
            f.write('# The topfile used is:\n')
            f.write('#    {:s}\n'.format(self.toppath))
            f.write('# The charge_file used is:\n')
            f.write('#    {:s}\n\n'.format(self.file_line_chargepath))
            if len(self.file_line_symmetry) != 0:
                f.write('# The symmetry_list used is:\n')
                f.write('#    {:s}\n\n'.format(self.file_line_symmetry))
            for i in topnamelist:
                f.write(i)
                f.write('\n')

