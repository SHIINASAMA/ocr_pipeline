from PySide6.QtGui import QIcon, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QMessageBox, QFileDialog
from app.resources.main_window_ui import Ui_MainWindow
import cv2
from easyocr import Reader
import os

# include the resource file
import app.resources.resource # type: ignore

class MainWindow:
    def __init__(self, window):
        self.window = window
        self.window.setWindowIcon(QIcon(':/assets/logo.png'))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.window)
        self.ui.select_image_btn.clicked.connect(self.select_image)
        self.ui.run_ocr_btn.clicked.connect(self.run_ocr)
        self.ui.show_image_btn.clicked.connect(self.show_result_image)
        self.ui.gen_code_btn.clicked.connect(self.gen_code)

        self.model = QStandardItemModel()
        self.ui.table_view.setModel(self.model)

        # TODO 变换并检测边缘
        self.ui.enable_main_body.setEnabled(False)
        # 不允许更改语言列表
        self.ui.lang_input.setEnabled(False)

        self.table_headers = ['内容', 'ROI', '键名称']
        self.image = None
        self.result_image = None
        self.image_path = None

    def select_image(self):
        self.image_path, _ = QFileDialog.getOpenFileName(self.window, "选择图片", "", "图片 (*.png *.xpm *.jpg *.jpeg)")
        if self.image_path:
            self.ui.image_path.setText(self.image_path)

    def run_ocr(self):
        if self.image_path is None:
            QMessageBox.warning(self.window, "错误", "请先选择一张图片")
            return
        self.image = cv2.imread(self.image_path)

        if self.ui.enable_gray.isChecked():
            self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)

        if self.ui.enable_gass_blur.isChecked():
            self.image = cv2.GaussianBlur(self.image, (5, 5), 0)

        if self.ui.enable_edged.isChecked():
            self.image = cv2.Canny(self.image, 75, 200)

        # 分割字符使用逗号
        lang_list = self.ui.lang_input.text().split(',')
        # 去掉空格
        lang_list = [lang.strip() for lang in lang_list if lang.strip()]

        reader = Reader(lang_list=lang_list)
        results = reader.readtext(self.image)
        self.result_image = self.image.copy()

        self.model.clear()
        self.model.setHorizontalHeaderLabels(self.table_headers)
        for (bbox, text, prob) in results:
            items = []
            items.append(QStandardItem(text))
            (tl, tr, br, bl) = bbox
            tl = (int(tl[0]), int(tl[1]))
            tr = (int(tr[0]), int(tr[1]))
            br = (int(br[0]), int(br[1]))
            bl = (int(bl[0]), int(bl[1]))
            cv2.rectangle(self.result_image, tl, br, (0, 255, 0), 2)
            # cv2.putText(self.result_image, text, (tl[0], tl[1] + 10),
            # cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            x1 = min(tl[0], bl[0])
            x2 = max(tr[0], br[0])
            h1 = min(tl[1], tr[1])
            h2 = max(bl[1], br[1])
            pos = f'[{h1}:{h2}, {x1}:{x2}]'
            items.append(QStandardItem(pos))
            self.model.appendRow(items)
        self.ui.table_view.resizeColumnsToContents()

    def show_result_image(self):
        if self.result_image is None:
            QMessageBox.warning(self.window, "错误", "请先执行一次OCR")
            return
        
        # filename, _ = QFileDialog.getSaveFileName(self.window, "保存位置")
        # if filename:
        filename = 'temp.png'
        if cv2.imwrite(filename, self.result_image):
            os.system('start {}'.format(filename))
        else:
            QMessageBox.warning(self.window, '错误', '输出图片失败')

    def gen_code(self):
        if self.model.rowCount() == 0:
            QMessageBox.warning(self.window, "错误", "请先执行一次OCR")
            return
        
        lang_list = self.ui.lang_input.text()
        with open('temp.py', 'w', encoding='utf-8') as f:
            # 遍历模型
            for row in range(self.model.rowCount()):
                if self.model.item(row, 2) is None:
                    continue
                key_name = self.model.item(row, 2).text()
                range_str =  self.model.item(row, 1).text()
                f.write("""
def get_{}(image):
	roi = image{}
	reader = easyocr.Reader(lang_list='{}')
	results = reader.readtext(roi)
	return results[0].text
""".format(key_name, range_str, lang_list))
