# encoding: utf-8
'''
@author:     Juncheng Chen

@copyright:  1999-2015 Alibaba.com. All rights reserved.

@license:    Apache Software License 2.0

@contact:    juncheng.cjc@outlook.com
'''
import csv,os,sys

from report.extlib import xlsxwriter

BaseDir=os.path.dirname(__file__)
sys.path.append(os.path.join(BaseDir,'../..'))


class Excel(object):

    def __init__(self, excel_file):
        self.excel_file = excel_file
        self.workbook = xlsxwriter.Workbook(excel_file)
        self.color_list = ["black", "blue", "brown", "green", "purple", "cyan", "red", "gray", "magenta", "navy", "lime", "orange", "yellow", "purple", "pink", "silver"]

    def add_sheet(self, sheet_name, x_axis, y_axis, headings, lines):
        worksheet = self.workbook.add_worksheet(sheet_name)
        worksheet.write_row('A1', headings)
        for i, line in enumerate(lines, 2):
            worksheet.write_row('A%d' % i, line)
        columns = len(headings)
        rows = len(lines)
        if columns > 1 and rows > 1:
            chart = self.workbook.add_chart({'type': 'line'})
            for j in range(1, columns):
                chart.add_series({'name':       [sheet_name, 0, j],
                                  'categories': [sheet_name, 1, 0, rows, 0],
                                  'values':     [sheet_name, 1, j, rows, j]})
            chart.set_title ({'name': sheet_name.replace('.', ' ').title()})
            chart.set_x_axis({'name': x_axis})
            chart.set_y_axis({'name': y_axis})
            worksheet.insert_chart('B3', chart, {'x_scale': 2, 'y_scale': 2})
    
    def save(self):
        self.workbook.close()

    def csv_to_xlsx(self, csv_file, sheet_name, x_axis, y_axis, y_fields=[], y_second_axis="", y_second_fields=[], cut_last_line_num=0, sheet_type='line'):
        '''
        把csv的数据存到excel中，并画曲线
        csv_file csv 文件路径 表格名
        sheet_name 图表名
        x_axis 横轴名 和 表中做横轴字段名
        y_axis 纵轴名
        y_fields 纵轴表中数据字段名 ，可以多个
        cut_last_line_num 如果有中文标题的话，截掉这行以及后面的
        '''
        filename = os.path.splitext(os.path.basename(csv_file))[0]
        logger.debug("filename:"+filename)
        worksheet = self.workbook.add_worksheet(filename)  # 创建一个sheet表格
        with open(csv_file, 'r', encoding='utf-8') as f:
            read = csv.reader(f)
            # read = csv.DictReader(f)
            # 行数
            l = 0
            # 表头
            headings = []
            for line in read:
                # print(line)
                r = 0

                for i in range(0, len(line)):
                # for i in line:
                    # print(i)
                    if self.is_number(line[i]):
                        if l == 0 or i == 0 or float(line[i]) != 0 : # 除标题行外和首列，结果为0的数据就不画图了，因为数据是来自于xlsx文件的，所以结果为0的话，对应的单元格也为空
                            worksheet.write(l, r, float(line[i]))  # 一个一个将单元格数据写入
                    else:
                        worksheet.write(l, r, line[i])
                    r = r + 1
                if l==0:
                    headings=line
                l = l + 1
                # 列数
            columns = len(headings)
        # 求出展示数据索引
        indexs=[]
        # 求出系列名所在索引
        series_index=[]
        for columu_name in y_fields:
            indexs.extend([i for i, v in enumerate(headings) if v == columu_name])
        series_index.extend([i for i, v in enumerate(headings) if v == "package"])
        logger.debug(series_index)
        if columns > 1 and l>2:
            chart = self.workbook.add_chart({'type': sheet_type})
            # 画图
            i =0
            for index in indexs:
                if "pid_cpu%" == headings[index] or "pid_pss(MB)" == headings[index]:
                    chart.add_series({
                        # 这个是series 系列名 包名
                        'name': [filename,1,series_index[i]],
                        'categories': [filename, 1, 0, l - cut_last_line_num - 1, 0],
                        'values': [filename, 1, index, l - cut_last_line_num - 1, index],
                        sheet_type:{'color': self.color_list[index%len(self.color_list)]}
                    })
                    i = i+1
                else:
                    chart.add_series({
                        'name': [filename, 0, index],
                        'categories': [filename, 1, 0, l - cut_last_line_num - 1, 0],
                        'values': [filename, 1, index, l - cut_last_line_num - 1, index],
                        sheet_type: {'color': self.color_list[index % len(self.color_list)]}
                        # list(np.random.choice(range(256), size=3))
                    })

            # 图表名
            chart.set_title ({'name':sheet_name})
            chart.set_x_axis({'name': x_axis})
            chart.set_y_axis({'name': y_axis})

            # Configure a series with a secondary axis
            # 求出展示数据索引
            if y_second_axis and len(y_second_fields) > 0:
                indexs2 = []
                for columu_name in y_second_fields:
                    indexs2.extend([i for i, v in enumerate(headings) if v == columu_name])
                for index2 in indexs2:
                    chart.add_series({
                        'name': [filename, 0, index2],
                        'categories': [filename, 1, 0, l - cut_last_line_num - 1, 0],
                        'values': [filename, 1, index2, l - cut_last_line_num - 1, index2],
                        sheet_type: {'color': self.color_list[index2 % len(self.color_list)]},
                        'y2_axis': 1 #???
                    })
                chart.set_y2_axis({'name': y_second_axis})

            worksheet.insert_chart('L3', chart, {'x_scale': 2, 'y_scale': 2})

    def csv_to_xlsx_combine(self, csv_file, sheet_name, x_axis, y_axis, y_fields=[], cut_last_line_num=0, sheet_type='column', addition_column = [], addition_sheet_type ='line'):
        '''
        把csv的数据存到excel中，并画曲线
        csv_file csv 文件路径 表格名
        sheet_name 图表名
        x_axis 横轴名 和 表中做横轴字段名
        y_axis 纵轴名
        y_fields 纵轴表中数据字段名 ，可以多个
        cut_last_line_num 如果有中文标题的话，截掉这行以及后面的
        addition_column 额外需要用其他类型的图表展示的列
        addition_sheet_type额外需要展示的图表类型
        '''
        filename = os.path.splitext(os.path.basename(csv_file))[0]
        logger.debug("filename:"+filename)
        worksheet = self.workbook.add_worksheet(filename)  # 创建一个sheet表格
        with open(csv_file, 'r', encoding='utf-8') as f:
            read = csv.reader(f)
            # read = csv.DictReader(f)
            # 行数
            l = 0
            # 表头
            headings = []
            for line in read:
                # print(line)
                r = 0

                for i in range(0, len(line)):
                # for i in line:
                    # print(i)
                    if self.is_number(line[i]):
                        if l == 0 or i == 0 or float(line[i]) != 0 : # 除标题行外和首列，结果为0的数据就不画图了，因为数据是来自于xlsx文件的，所以结果为0的话，对应的单元格也为空
                            worksheet.write(l, r, float(line[i]))  # 一个一个将单元格数据写入
                    else:
                        worksheet.write(l, r,line[i])
                    r = r + 1
                if l==0:
                    headings=line
                l = l + 1
                # 列数
            columns = len(headings)
        # 求出展示数据索引
        indexs=[]
        addi_indexs= []
        # 求出系列名所在索引
        series_index=[]
        for columu_name in y_fields:
            indexs.extend([i for i, v in enumerate(headings) if v == columu_name])
        for columu_name in addition_column:
            addi_indexs.extend([i for i, v in enumerate(headings) if v == columu_name])
        series_index.extend([i for i, v in enumerate(headings) if v == "package"])
        logger.debug(series_index)
        if columns > 1 and l > 2:
            chart = self.workbook.add_chart({'type': sheet_type,"subtype":"stacked"})
            # 画图
            i =0
            for index in indexs:
                if "pid_cpu%" == headings[index] or "pid_pss(MB)" == headings[index]:
                    chart.add_series({
                        # 这个是series 系列名 包名
                        'name': [filename,1,series_index[i]],
                        'categories': [filename, 1, 0, l - cut_last_line_num - 1, 0],
                        'values': [filename, 1, index, l - cut_last_line_num - 1, index],
                        'line':{'color': self.color_list[index%len(self.color_list)]}
                    })
                    i = i+1
                else:
                    chart.add_series({
                        'name': [filename, 0, index],
                        'categories': [filename, 1, 0, l - cut_last_line_num - 1, 0],
                        'values': [filename, 1, index, l - cut_last_line_num - 1, index],
                        'line': {'color': self.color_list[index % len(self.color_list)]}
                        # list(np.random.choice(range(256), size=3))
                    })
            for addi_index in addi_indexs:
                # if "pid_cpu%" == headings[index] or "pid_pss(MB)" == headings[index]:
                #     chart.add_series({
                #         # 这个是series 系列名 包名
                #         'name': [filename,1,series_index[i]],
                #         'categories': [filename, 1, 0, l - cut_last_line_num - 1, 0],
                #         'values': [filename, 1, index, l - cut_last_line_num - 1, index],
                #         'line':{'color': self.color_list[index%len(self.color_list)]}
                #     })
                #     i = i+1
                # el
                if len(addition_column) != 0 and addition_sheet_type:
                    line_chart = self.workbook.add_chart({'type': addition_sheet_type})
                    line_chart.add_series({
                        'name': [filename, 0, addi_index],
                        'categories': [filename, 1, 0, l - cut_last_line_num - 1, 0],
                        'values': [filename, 1, addi_index, l - cut_last_line_num - 1, addi_index],
                        'line': {'color': self.color_list[addi_index % len(self.color_list)]}
                    })
            # 图表名
            chart.set_title ({'name':sheet_name})
            chart.set_x_axis({'name': x_axis})
            chart.set_y_axis({'name': y_axis})
            chart.combine(line_chart)
            worksheet.insert_chart('L3', chart, {'x_scale': 2, 'y_scale': 2})

    def is_number(self,s):
        try:
            float(s)
            return True
        except ValueError:
            pass

        try:
            import unicodedata
            unicodedata.numeric(s)
            return True
        except (TypeError, ValueError):
            pass

        return False

if __name__ == '__main__':
    book_name = 'summary.xlsx'
    excel = Excel(book_name)
    # excel.csv_to_xlsx("mem_infos_10-42-38.csv","meminfo","datetime","mem(MB)",["pid_pss(MB)","pid_alloc_heap(MB)"])
    excel.csv_to_xlsx("/Users/look/Desktop/project/mobileperf-mac/results/com.alibaba.ailabs.genie.launcher/2019_03_05_23_55_28/cpuinfo.csv",
                      "pid_cpu","datetime","%",["pid_cpu%","total_pid_cpu%"])
    excel.save()
