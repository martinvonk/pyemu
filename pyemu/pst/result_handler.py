import os
import pandas as pd
import pyemu


class ResultHandler(object):
    def __init__(self,m_d,case):
        self.m_d = m_d
        self.case = case
        self.path2files = [os.path.join(self.m_d,f.lower()) for f in os.listdir(self.m_d)]
        self.results_loaded = {}
        self.failed2load_files = []
        #todo: check that m_ds are infact valid master dirs


    @property
    def files_loaded(self):
        files = list(self.results_loaded.keys())
        files.sort()
        return files
    

    def get_or_load_csv_file(self,filename,index_col=None):
        if len(os.path.split(filename)[0]) == 0:
            filename = os.path.join(self.m_d,filename)
        if filename in self.results_loaded:
            return self.results_loaded[filename]
        else:
            df = None
            try:
                df = pd.read_csv(filename,index_col=index_col)
                self.results_loaded[filename] = df
            except Exception as e:
                print("error loading file '{0}': {1}".format(filename, str(e)))
                self.failed2load_files.append([filename, str(e)])
            return df

    def get_or_load_ensemble_file(self, filename,index_name="realization"):
        if len(os.path.split(filename)) == 1:
            filename = os.path.join(self.m_d,filename)
        if filename in self.results_loaded:
            return self.results_loaded[filename]
        else:
            df = None
            try:
                if filename.lower().endswith(".csv"):
                    df = pd.read_csv(filename, index_col=0)
                elif filename.lower().endswith(".jcb") or filename.lower().endswith(".jco") or filename.lower().endswith(".bin"):
                    df = pyemu.Matrix.from_binary(filename).to_dataframe()
                else:
                    raise Exception("unrecognized ensemble/population file extension: '{0}', should be csv, jcb/jco, or bin".\
                                    format(filename))
                df.index.name = index_name
                self.results_loaded[filename] = df
            except Exception as e:
                print("error loading file '{0}': {1}".format(filename,str(e)))
                self.failed2load_files.append([filename,str(e)])
            return df

    def check_dup_iters(self,itrs, files):
        dup_itrs,dup_files = [],[]
        for i,itr in enumerate(itrs[:-1]):
            if itr in itrs[i+1:]:
                dup_itrs.append(str(itr))
                dup_files.append(files[i])
        if len(dup_files) > 0:
            print("dup files: {0}".format("\n".join(dup_files)))
            print("dup itrs: {0}".format("\n".join(dup_itrs)))
            raise Exception("duplicate iteration tags found")


    def parse_iter_from_tag(self,tag):
        rtag = tag[::-1]
        digits = []
        for d in rtag:
            if str.isalpha(d):
                break
            digits.append(d)
        if len(digits) == 0:
            return None
        digits = digits[::-1]
        #itr = int(''.join(digits))
        itr = ''.join(digits)
        return itr

class ResultIesHandler(ResultHandler):

    def get_files(self,tag):
        files = []
        case_tag = self.case + tag

        for f in self.path2files:
            if tag in f.lower() and\
                os.path.split(f)[1].lower().startswith(self.case+".") and \
                len(os.path.split(f)[1].split(".")) == 4:
                try:
                    itr = int(os.path.split(f)[1].split(".")[1])
                except Exception as e:
                    pass
                else:
                    files.append(f)
            elif case_tag in os.path.split(f)[1].lower():
                files.append(f)
        return files


    def __getattr__(self,tag):
        tag = tag.lower().strip()
        if tag.startswith("paren") or tag.startswith("obsen"):
            itr = self.parse_iter_from_tag(tag)
            ttag = tag[:3]
            #load the combined ensemble
            if itr is None:
                file_tag = ".{0}.".format(ttag)
                files = self.get_files(file_tag)
                if len(files) == 0:
                    raise Exception("ResultsIesHandler: no files found for tag '{0}' using file_tag '{1}'".\
                                    format(tag,file_tag))
                itrs = [int(os.path.split(f)[1].split('.')[1]) for f in files]
                self.check_dup_iters(itrs,files)
                d = {i:f for i,f in zip(itrs,files)}
                itrs.sort()
                dfs = []
                for itr in itrs:
                    df = self.get_or_load_ensemble_file(d[itr])
                    dfs.append(df)
                if len(dfs) == 0:
                    return None
                if len(dfs) > 1:
                    df = pd.concat(dfs,keys=itrs,names=["iteration","realization"])
                else:
                    df = dfs[0]
                return df
            else:
                file_tag = ".{0}.{1}.".format(int(itr),ttag)
                files = self.get_files(file_tag)
                if len(files) != 1:
                    #todo something here...
                    print(files)
                    raise Exception()

                df = self.get_or_load_ensemble_file(files[0])
                return df


        elif tag.startswith("phi"):
            phi_type = tag.split("_")[1]
            csv_filename = "{0}.phi.{1}.csv".format(self.case,phi_type)
            df = self.get_or_load_csv_file(csv_filename)
            return df

        elif tag.startswith("noise"):
            files = self.get_files(".obs+noise.")
            if len(files) != 1:
                raise Exception("expected 1 noise ensemble file, found {0}: {1}".\
                                format(len(files),','.join(files)))
            df = self.get_or_load_ensemble_file(files[0])
            return df
        elif tag.startswith("weights"):
            files = self.get_files(".weights.")
            if len(files) != 1:
                raise Exception("expected 1 weight ensemble file, found {0}: {1}". \
                                format(len(files), ','.join(files)))
            df = self.get_or_load_ensemble_file(files[0])
            return df

        elif tag.startswith("pdc"):
            itr = self.parse_iter_from_tag(tag)
            ttag = tag
            if itr is not None:
                ttag = tag.replace(itr,"")
            # load the combined ensemble
            if itr is None:
                file_tag = ".{0}.".format(ttag)
                files = self.get_files(file_tag)
                if len(files) == 0:
                    raise Exception()
                itrs = [int(os.path.split(f)[1].split('.')[1]) for f in files]
                self.check_dup_iters(itrs, files)
                d = {i: f for i, f in zip(itrs, files)}
                itrs.sort()
                dfs = []
                for itr in itrs:
                    df = self.get_or_load_csv_file(d[itr],index_col=0)
                    dfs.append(df)
                if len(dfs) == 0:
                    return None
                if len(dfs) > 1:
                    df = pd.concat(dfs, keys=itrs, names=["iteration", "name"])
                else:
                    df = dfs[0]
                return df
            else:
                file_tag = ".{0}.{1}.".format(int(itr), ttag)
                files = self.get_files(file_tag)
                if len(files) != 1:
                    # todo something here...
                    print(files)
                    raise Exception("expecting to find 1 file for tag '{0}', iter {1} (org tag {2})"\
                                    .format(ttag,itr,tag))

                df = self.get_or_load_ensemble_file(files[0])
                return df

        elif tag.startswith("pcs"):
            itr = self.parse_iter_from_tag(tag)
            ttag = tag
            if itr is not None:
                ttag = tag.replace(itr, "")
            # load the combined ensemble
            if itr is None:
                file_tag = ".{0}.".format(ttag)
                files = self.get_files(file_tag)
                if len(files) == 0:
                    raise Exception()
                itrs = [int(os.path.split(f)[1].split('.')[1]) for f in files]
                self.check_dup_iters(itrs, files)
                d = {i: f for i, f in zip(itrs, files)}
                itrs.sort()
                dfs = []
                for itr in itrs:
                    df = self.get_or_load_csv_file(d[itr],index_col=0)
                    dfs.append(df)
                if len(dfs) == 0:
                    return None
                if len(dfs) > 1:
                    df = pd.concat(dfs, keys=itrs, names=["iteration", "group"])
                else:
                    df = dfs[0]
                return df
            else:
                file_tag = ".{0}.{1}.".format(int(itr), ttag)
                files = self.get_files(file_tag)
                if len(files) != 1:
                    # todo something here...
                    raise Exception()

                df = self.get_or_load_ensemble_file(files[0])
                return df



        else:
            raise Exception("ResultIesHandler has no attribute '{0}'".format(tag))




class ResultMouHandler(ResultHandler):

    def get_files(self,tag):
        files = []
        case_tag = self.case + tag

        for f in self.path2files:
            if "stack" in tag and "nested" not in tag and "nested" in f:
                continue
            if "pop" in tag and "archive" not in tag and "archive" in f:
                continue
            if "pop" in tag and "chance" not in tag and "chance" in f:
                continue
            if tag in f.lower() and\
                os.path.split(f)[1].lower().startswith(self.case+"."):
                try:
                    itr = int(os.path.split(f)[1].split(".")[1])
                except Exception as e:
                    pass
                else:
                    files.append(f)
        return files





    def __getattr__(self,tag):
        tag = tag.lower().strip()

        if (tag.startswith("dvpop") or tag.startswith("obspop") or \
                tag.startswith("archivedvpop") or tag.startswith("archiveobspop") \
                or tag.startswith("chancedvpop") or tag.startswith("chanceobspop")):
            itr = self.parse_iter_from_tag(tag)
            ttag = "dv_pop"
            if "obs" in tag:
                ttag = "obs_pop"
            if "archive" in tag:
                ttag = "archive."+ttag
            elif "chance" in tag:
                ttag = "chance."+ttag
            # load the combined ensemble
            if itr is None:
                file_tag = ".{0}.".format(ttag)
                files = self.get_files(file_tag)
                if len(files) == 0:
                    raise Exception("no files found for tag '{0}'".format(file_tag))
                itrs = [int(os.path.split(f)[1].split('.')[1]) for f in files]
                self.check_dup_iters(itrs, files)
                d = {i: f for i, f in zip(itrs, files)}
                itrs.sort()
                dfs = []
                for itr in itrs:
                    df = self.get_or_load_ensemble_file(d[itr],index_name="member")
                    dfs.append(df)
                if len(dfs) == 0:
                    return None
                if len(dfs) > 1:
                    df = pd.concat(dfs, keys=itrs, names=["generation", "member"])
                else:
                    df = dfs[0]
                return df
            else:
                file_tag = ".{0}.{1}.".format(int(itr), ttag)
                files = self.get_files(file_tag)
                if len(files) != 1:
                    # todo something here...
                    print(files)
                    raise Exception()

                df = self.get_or_load_ensemble_file(files[0],index_name="member")
                return df


        elif tag == "paretosum_archive" or tag == "paretosum":

            csv_filename = "{0}.pareto.summary.csv".format(self.case)
            if "archive" in tag:
                csv_filename = "{0}.pareto.archive.summary.csv".format(self.case)
            df = self.get_or_load_csv_file(csv_filename)
            return df


        elif tag.startswith("parstack") or tag.startswith("obsstack") or \
                tag.startswith("nestedparstack") or tag.startswith("nestedobstack"):
            itr = self.parse_iter_from_tag(tag)
            ttag = "par_stack"
            if "obs" in tag:
                ttag = "obs_stack"
            if "nested" in tag:
                ttag = "nested." + ttag
            # load the combined ensemble
            if itr is None:
                file_tag = ".{0}.".format(ttag)
                files = self.get_files(file_tag)
                if len(files) == 0:
                    raise Exception()
                itrs = [int(os.path.split(f)[1].split('.')[1]) for f in files]
                self.check_dup_iters(itrs,files)
                d = {i: f for i, f in zip(itrs, files)}
                itrs.sort()
                dfs = []
                for itr in itrs:
                    df = self.get_or_load_ensemble_file(d[itr])
                    if "nested" in tag:
                        df["realization"] = df.index.map(lambda x: x.split("||")[0])
                        df.index = df.index.map(lambda x: x.split("||")[1])

                    dfs.append(df)
                if len(dfs) == 0:
                    return None
                if "nested" in tag:
                    df = pd.concat(dfs, keys=itrs, names=["generation", "member"])
                else:
                    if len(dfs) > 1:
                        df = pd.concat(dfs, keys=itrs, names=["generation", "member"])
                    else:
                        df = dfs[0]

                return df
            else:
                file_tag = ".{0}.{1}.".format(int(itr), ttag)
                files = self.get_files(file_tag)
                if len(files) != 1:
                    # todo something here...
                    raise Exception()

                df = self.get_or_load_ensemble_file(files[0])
                if "nested" in tag:
                    df["realization"] = df.index.map(lambda x: x.split("||")[0])
                    df.index = df.index.map(lambda x: x.split("||")[1])
                    df.index.name = "member"
                return df


        elif tag.startswith("stack_summary"):
            itr = self.parse_iter_from_tag(tag)
            ttag = "population_stack_summary"
            # load the combined ensemble
            if itr is None:
                file_tag = ".{0}.".format(ttag)
                files = self.get_files(file_tag)
                if len(files) == 0:
                    raise Exception()
                itrs = [int(os.path.split(f)[1].split('.')[1]) for f in files]
                self.check_dup_iters(itrs, files)
                d = {i: f for i, f in zip(itrs, files)}
                itrs.sort()
                dfs = []
                for itr in itrs:
                    df = self.get_or_load_csv_file(d[itr], index_col=0)
                    dfs.append(df)
                if len(dfs) == 0:
                    return None
                if len(dfs) > 1:
                    df = pd.concat(dfs, keys=itrs, names=["generation", "member"])
                else:
                    df = dfs[0]
                return df
            else:
                file_tag = ".{0}.{1}.".format(int(itr), ttag)
                files = self.get_files(file_tag)
                if len(files) != 1:
                    # todo something here...
                    raise Exception()

                df = self.get_or_load_csv_file(files[0])
                return df

        else:
            raise Exception("ResultMouHandler has no attribute '{0}'".format(tag))


class Results(object):
    def __init__(self,m_d,case=None):
        if not os.path.exists(m_d):
            raise Exception("m_d '{0}' not found".format(m_d))
        if not os.path.isdir(m_d):
            raise Exception("m_d '{0}' is not directory".format(m_d))
        if case is None:
            pst_files = [f for f in os.listdir(m_d) if f.endswith(".pst")]
            if len(pst_files) == 0:
                raise Exception("no .pst files found in m_d '{0}'".format(m_d))
            elif len(pst_files) > 1:
                raise Exception("multiple .pst files found in m_d '{0}'".format(m_d))
            case = pst_files[0].replace(".pst","")
        self.m_d = m_d
        self.case = case
        self.ieshand = ResultIesHandler(self.m_d,self.case)
        self.mouhand = ResultMouHandler(self.m_d,self.case)


    def __getattr__(self,tag):

        if tag == "ies":
            return self.ieshand
        elif tag == "mou":
            return self.mouhand
        else:
            raise Exception()





